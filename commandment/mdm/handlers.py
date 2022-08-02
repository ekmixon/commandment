from binascii import hexlify

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from flask import current_app
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from commandment.apps import ManagedAppStatus
from commandment.apps.models import ManagedApplication
from commandment.mdm import commands
from commandment.mdm.app import command_router
from .commands import ProfileList, DeviceInformation, SecurityInfo, InstalledApplicationList, CertificateList, \
    InstallProfile, AvailableOSUpdates, InstallApplication, RemoveProfile, ManagedApplicationList
from .response_schema import InstalledApplicationListResponse, DeviceInformationResponse, AvailableOSUpdateListResponse, \
    ProfileListResponse, SecurityInfoResponse
from ..models import db, Device, Command as DBCommand
from commandment.inventory.models import InstalledCertificate, InstalledProfile, InstalledApplication

Queries = DeviceInformation.Queries


@command_router.route('DeviceInformation')
def ack_device_information(request: DBCommand, device: Device, response: dict):
    """Acknowledge a response to the ``DeviceInformation`` command.

    Args:
        request (Command): An instance of the command that prompted the device to come back with this request.
        device (Device): The device responding to the command.
        response (dict): The raw response dictionary, de-serialized from plist.
    Returns:
        void: Reserved for future use

    See Also:
        - `DeviceInformation Command <https://developer.apple.com/library/content/documentation/Miscellaneous/Reference/MobileDeviceManagementProtocolRef/3-MDM_Protocol/MDM_Protocol.html#//apple_ref/doc/uid/TP40017387-CH3-SW15>`_.
    """
    schema = DeviceInformationResponse()
    result = schema.load(response)
    for k, v in result.data['QueryResponses'].items():
        setattr(device, k, v)

    db.session.commit()


@command_router.route('SecurityInfo')
def ack_security_info(request: DBCommand, device: Device, response: dict):
    schema = SecurityInfoResponse()
    result = schema.load(response)


    db.session.commit()


@command_router.route('ProfileList')
def ack_profile_list(request: DBCommand, device: Device, response: dict):
    """Acknowledge a ``ProfileList`` response.

    This is used as the trigger to perform InstallProfile/RemoveProfiles as we have the most current data about
    what exists on the device.

    The set of profiles to install is a result of:

        set(desired) - set(installed) = set(install)

    The set of profiles to remove is a result of:

        set(installed) - set(desired) = set(remove)

    EXCEPT THAT:
        - You never want to remove the enrollment profile unless you are "unmanaging" the device.
        - You can't remove profiles not installed by this MDM.

    Args:
        request (ProfileList): The command instance that generated this response.
        device (Device): The device responding to the command.
        response (dict): The raw response dictionary, de-serialized from plist.
    Returns:
          void: Reserved for future use
    """
    schema = ProfileListResponse()
    profile_list = schema.load(response)

    for pl in device.installed_payloads:
        db.session.delete(pl)

    # Impossible to calculate delta, so all profiles get wiped
    for p in device.installed_profiles:
        db.session.delete(p)

    desired_profiles = {}
    for tag in device.tags:
        for p in tag.profiles:
            desired_profiles[p.uuid] = p

    remove_profiles = []

    for profile in profile_list.data['ProfileList']:
        profile.device = device

        # device.udid may have dashes (macOS) or not (iOS)
        profile.device_udid = device.udid

        for payload in profile.payload_content:
            payload.device = device
            payload.profile_id = profile.id

        db.session.add(profile)

        # Reconcile profiles which should be installed
        if profile.payload_uuid in desired_profiles:
            del desired_profiles[profile.payload_uuid]
        elif profile.is_managed:
            current_app.logger.debug("Going to remove: %s", profile.payload_display_name)
            remove_profiles.append(profile)

        else:
            current_app.logger.debug("Skipping removal of unmanaged profile: %s", profile.payload_display_name)
    # Queue up some desired profiles
    for p in desired_profiles.values():
        c = commands.InstallProfile(None, profile=p)
        dbc = DBCommand.from_model(c)
        dbc.device = device
        db.session.add(dbc)

    for remove_profile in remove_profiles:
        c = commands.RemoveProfile(None, Identifier=remove_profile.payload_identifier)
        dbc = DBCommand.from_model(c)
        dbc.device = device
        db.session.add(dbc)

    db.session.commit()


@command_router.route('CertificateList')
def ack_certificate_list(request: DBCommand, device: Device, response: dict):
    """Acknowledge a response to the ``CertificateList`` command.

    Args:
        request (Command): An instance of the command that prompted the device to come back with this request.
        device (Device): The database model of the device responding.
        response (dict): The response plist data, as a dictionary.

    Returns:
        void: Nothing is returned but this behaviour is subject to change.
    """
    for c in device.installed_certificates:
        db.session.delete(c)

    certificates = response['CertificateList']
    current_app.logger.debug(
        f'Received CertificatesList response containing {len(certificates)} certificate(s)'
    )


    for cert in certificates:
        ic = InstalledCertificate()
        ic.device = device
        ic.device_udid = device.udid

        ic.x509_cn = cert.get('CommonName', None)
        ic.is_identity = cert.get('IsIdentity', None)

        der_data = cert['Data']
        certificate = x509.load_der_x509_certificate(der_data, default_backend())
        ic.fingerprint_sha256 = hexlify(certificate.fingerprint(hashes.SHA256()))
        ic.der_data = der_data

        db.session.add(ic)

    db.session.commit()


@command_router.route('InstalledApplicationList')
def ack_installed_app_list(request: DBCommand, device: Device, response: dict):
    """Acknowledge a response to the ``InstalledApplicationList`` command.
    
    .. note:: There is no composite key which can uniquely identify an item in the installed applications list.
        Some applications may not contain any version information at all. For this reason, the entire list of installed
        applications is cleared before inserting a new list.
        
    Args:
          request (InstalledApplicationList): An instance of the command that generated this response from the managed
            device.
          device (Device): The device responding
          response (dict): The dictionary containing the parsed plist response from the device.
    Returns:
          void: Nothing is returned but this behaviour is subject to change.
    """

    for a in device.installed_applications:
        db.session.delete(a)

    applications = response['InstalledApplicationList']
    current_app.logger.debug(
        f'Received InstalledApplicationList response containing {len(applications)} application(s)'
    )


    schema = InstalledApplicationListResponse()
    result, errors = schema.load(response)
    current_app.logger.debug(errors)
    # current_app.logger.info(result)

    ignored_app_bundle_ids = current_app.config['IGNORED_APPLICATION_BUNDLE_IDS']

    for ia in result['InstalledApplicationList']:
        if isinstance(ia, db.Model):
            if ia.bundle_identifier in ignored_app_bundle_ids:
                current_app.logger.debug('Ignoring app with bundle id: %s', ia.bundle_identifier)
                continue

            ia.device = device
            ia.device_udid = device.udid
            db.session.add(ia)
        else:
            current_app.logger.debug('Not a model: %s', ia)

    db.session.commit()


@command_router.route('InstallProfile')
def ack_install_profile(request: DBCommand, device: Device, response: dict):
    """Acknowledge a response to ``InstallProfile``."""
    pass


@command_router.route('RemoveProfile')
def ack_install_profile(request: DBCommand, device: Device, response: dict):
    """Acknowledge a response to ``RemoveProfile``."""
    pass


@command_router.route('AvailableOSUpdates')
def ack_available_os_updates(request: DBCommand, device: Device, response: dict):
    """Acknowledge a response to AvailableOSUpdates"""
    if response.get('Status', None) != 'Error':
        for au in device.available_os_updates:
            db.session.delete(au)

        schema = AvailableOSUpdateListResponse()
        result = schema.load(response)

        for upd in result.data['AvailableOSUpdates']:
            upd.device = device
            db.session.add(upd)

        db.session.commit()


@command_router.route('InstallApplication')
def ack_install_application(request: DBCommand, device: Device, response: dict):
    """Acknowledge a response to InstallApplication.

    We will insert this into `managed_applications` to show that there is a pending application install.
    `managed_applications` will be the source of truth for installation status.

    If the result of `InstallApplication` is a user prompt, we cannot send further IA commands until the prompt has
    been resolved(?) as seen on iOS 11.3.1

    TODO: Also create a pending status when the command is queued but not acked
    """
    if response.get('Status', None) != 'Error':
        try:
            # It is possible to send `InstallApplication` and receive Acknowledged multiple times for the same app,
            # so we want to avoid multiple rows in that scenario
            ma = db.session.query(ManagedApplication).filter(
                Device.id == device.id,
                ManagedApplication.bundle_id == response['Identifier']
            ).one()
            ma.ia_command = request
            db.session.commit()

        except NoResultFound:
            ma = ManagedApplication()
            ma.device = device
            ma.bundle_id = response['Identifier']
            ma.status = ManagedAppStatus(response['State'])
            ma.ia_command = request

            db.session.add(ma)
            db.session.commit()


@command_router.route('ManagedApplicationList')
def ack_managed_application_list(request: DBCommand, device: Device, response: dict):
    """Acknowledge a response to `ManagedApplicationList`."""
    if response.get('Status', None) == 'Error':
        return
    for bundle_id, status in response['ManagedApplicationList'].items():
        try:
            ma = db.session.query(ManagedApplication).filter(
                Device.id == device.id,
                ManagedApplication.bundle_id == bundle_id
            ).one()
        except NoResultFound:
            ma = ManagedApplication(bundle_id=bundle_id, device=device)

        ma.status = ManagedAppStatus(status['Status'])
        ma.external_version_id = status.get('ExternalVersionIdentifier', None)  # Does not exist in iOS 11.3.1
        ma.has_configuration = status['HasConfiguration']
        ma.has_feedback = status['HasFeedback']
        ma.is_validated = status['IsValidated']
        ma.management_flags = status['ManagementFlags']

        db.session.add(ma)

    db.session.commit()

    for tag in device.tags:
        for app in tag.applications:
            # TODO: need to check with new versions being available. This is very primitive.
            if app.bundle_id in response['ManagedApplicationList'].keys():
                continue

            c = commands.InstallApplication(application=app)
            dbc = DBCommand.from_model(c)
            dbc.device = device
            db.session.add(dbc)

            ma = ManagedApplication(device=device, application=app, ia_command=dbc, status=ManagedAppStatus.Queued)
            db.session.add(ma)

    db.session.commit()


@command_router.route('RestartDevice')
def ack_restart_device(request: DBCommand, device: Device, response: dict):
    """Acknowledge a response to `RestartDevice`.

    On macOS 10.13.6, the MDM client comes back with an `Idle` check in upon restart as part of launchd starting up.
    This happens BEFORE the loginwindow (at about 40% of the progress bar at startup). This is the same Power-on
    behaviour.
    """
    pass


@command_router.route('ShutDownDevice')
def ack_restart_device(request: DBCommand, device: Device, response: dict):
    """Acknowledge a response to `ShutDownDevice`.

    On macOS 10.13.6, the MDM client comes back with an `Idle` check in upon restart as part of launchd starting up.
    This happens BEFORE the loginwindow (at about 40% of the progress bar at startup). This is the same Power-on
    behaviour.
    """
    pass
