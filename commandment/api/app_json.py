"""
This module contains API endpoints which do not fit with the JSON-API specification.
"""
import io
from flask import Blueprint, send_file, abort, current_app, jsonify, request, make_response
from sqlalchemy.orm.exc import NoResultFound
import plistlib
import string
from commandment.plistutil.nonewriter import dumps as dumps_none
from base64 import urlsafe_b64encode
from commandment.models import db, Organization, Device, Command
from commandment.pki.models import Certificate, RSAPrivateKey
from commandment.profiles.models import Profile
from commandment.mdm import commands, Platform
from .schema import OrganizationFlatSchema
from commandment.profiles.schema import ProfileSchema
from commandment.profiles.plist_schema import ProfileSchema as ProfilePlistSchema

flat_api = Blueprint('flat_api', __name__)

# @flat_api.errorhandler(400)
# def bad_request(e):
#     return jsonify({'errors': [
#         {
#             'status': '400',
#             'title': str(e),
#         }
#     ]}


@flat_api.route('/v1/organization', methods=['GET'])
def organization_get():
    """Retrieve information about the MDM home organization.

    Only returns a pseudo JSON-API representation because the standard has no definition for
    `singleton` resources.

    """
    try:
        o = db.session.query(Organization).one()
    except NoResultFound:
        return abort(400, 'No organization details found')
    
    org_schema = OrganizationFlatSchema()
    result = org_schema.dumps(o)

    return jsonify(result.data)


@flat_api.route('/v1/download/certificates/<int:certificate_id>')
def download_certificate(certificate_id: int):
    """Download a certificate in PEM format

    :reqheader Accept: application/x-pem-file
    :reqheader Accept: application/x-x509-user-cert
    :reqheader Accept: application/x-x509-ca-cert
    :resheader Content-Type: application/x-pem-file
    :resheader Content-Type: application/x-x509-user-cert
    :resheader Content-Type: application/x-x509-ca-cert
    :statuscode 200: OK
    :statuscode 404: There is no certificate configured
    :statuscode 400: Can't produce requested encoding
    """
    c = db.session.query(Certificate).filter(Certificate.id == certificate_id).one()
    bio = io.BytesIO(c.pem_data)

    return send_file(bio, 'application/x-pem-file', True, 'certificate.pem')


@flat_api.route('/v1/rsa_private_keys/<int:rsa_private_key_id>/download')
def download_key(rsa_private_key_id: int):
    """Download an RSA private key in PEM or DER format

    :reqheader Accept: application/x-pem-file
    :reqheader Accept: application/pkcs8
    :resheader Content-Type: application/x-pem-file
    :resheader Content-Type: application/pkcs8
    :statuscode 200: OK
    :statuscode 404: Not found
    :statuscode 400: Can't produce requested encoding
    """
    if not current_app.debug:
        abort(500, 'Not supported in this mode')

    c = db.session.query(RSAPrivateKey).filter(RSAPrivateKey.id == rsa_private_key_id).one()
    bio = io.BytesIO(c.pem_data)

    return send_file(bio, 'application/x-pem-file', True, 'rsa_private_key.pem')


@flat_api.route('/v1/devices/test/<int:device_id>', methods=['POST'])
def device_test(device_id: int):
    """Testing endpoint for quick and dirty command checking"""
    d = db.session.query(Device).filter(Device.id == device_id).one()

    #ia = commands.InstallApplication(ManifestURL='https://localhost:5443/static/appmanifest/munkitools-3.1.0.3430.plist')
    ia = commands.Settings(bluetooth=False)

    dbc = Command.from_model(ia)
    dbc.device = d
    db.session.add(dbc)

    db.session.commit()

    return 'OK'


@flat_api.route('/v1/devices/inventory/<int:device_id>')
def device_inventory(device_id: int):
    """Enqueue ALL inventory commands to refresh the device's entire inventory.
    
    :statuscode 200: OK
    """
    d = db.session.query(Device).filter(Device.id == device_id).one()

    # DeviceInformation
    di = commands.DeviceInformation.for_platform(d.platform, d.os_version)
    db_command = Command.from_model(di)
    db_command.device = d
    db.session.add(db_command)

    # InstalledApplicationList - Pretty taxing so don't run often
    # ial = commands.InstalledApplicationList()
    # db_command_ial = Command.from_model(ial)
    # db_command_ial.device = d
    # db.session.add(db_command_ial)

    # CertificateList
    cl = commands.CertificateList()
    dbc = Command.from_model(cl)
    dbc.device = d
    db.session.add(dbc)

    # SecurityInfo
    si = commands.SecurityInfo()
    dbsi = Command.from_model(si)
    dbsi.device = d
    db.session.add(dbsi)

    # ProfileList
    pl = commands.ProfileList()
    db_pl = Command.from_model(pl)
    db_pl.device = d
    db.session.add(db_pl)

    # AvailableOSUpdates
    au = commands.AvailableOSUpdates()
    au_pl = Command.from_model(au)
    au_pl.device = d
    db.session.add(au_pl)

    mal = commands.ManagedApplicationList()
    mal_pl = Command.from_model(mal)
    mal_pl.device = d
    db.session.add(mal_pl)

    db.session.commit()

    return 'OK'


@flat_api.route('/v1/devices/<int:device_id>/clear_passcode', methods=['POST'])
def clear_passcode(device_id: int):
    """Enqueues a ClearPasscode command for the device id specified.

    :reqheader Accept: application/vnd.api+json
    :reqheader Content-Type: ?
    :resheader Content-Type: application/vnd.api+json
    :statuscode 201: command created
    :statuscode 400: not applicable to this device
    :statuscode 404: device with this identifier was not found
    :statuscode 500: system error
    """
    d = db.session.query(Device).filter(Device.id == device_id).one()
    if d.platform == Platform.macOS:
        return abort(400, 'ClearPasscode is not supported on Mac computers')

    if d.unlock_token is None:
        return abort(400, 'No UnlockToken is available for this device')

    cp = commands.ClearPasscode(UnlockToken=urlsafe_b64encode(d.unlock_token).decode('utf-8'))
    cp_pl = Command.from_model(cp)
    cp_pl.device = d
    db.session.add(cp_pl)

    db.session.commit()

    return 'OK', 201, {}


@flat_api.route('/v1/devices/<int:device_id>/lock', methods=['POST'])
def lock(device_id: int):
    """Enqueues a DeviceLock command for the device id specified.

    If the target device is a macOS device, a 6 digit Find My Mac PIN will be automatically generated and stored
    with the device record (and also output in the response).

    :reqheader Accept: application/vnd.api+json
    :reqheader Content-Type: ?
    :resheader Content-Type: application/vnd.api+json
    :statuscode 201: command created
    :statuscode 400: not applicable to this device
    :statuscode 404: device with this identifier was not found
    :statuscode 500: system error
    """
    d = db.session.query(Device).filter(Device.id == device_id).one()
    if d.platform == Platform.macOS:
        return abort(400, 'Not Implemented')

    dl = commands.DeviceLock()
    dl_pl = Command.from_model(dl)
    dl_pl.device = d
    db.session.add(dl_pl)

    db.session.commit()

    return 'OK', 201, {}


@flat_api.route('/v1/devices/<int:device_id>/restart', methods=['POST'])
def restart(device_id: int):
    """Enqueues a RestartDevice command for the device id specified.

    :reqheader Accept: application/json
    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :statuscode 201: command created
    :statuscode 400: not applicable to this device. returned if this device is not supervised or not capable of taking command.
    :statuscode 404: device with this identifier was not found
    :statuscode 500: system error
    """
    d: Device = db.session.query(Device).filter(Device.id == device_id).one()

    if d.model_name == 'iPhone' and not d.is_supervised:
        return 'Cannot restart an unsupervised iOS device', 400, {}

    cmd = commands.RestartDevice()
    orm_cmd = Command.from_model(cmd)
    orm_cmd.device = d
    db.session.add(orm_cmd)

    db.session.commit()

    return 'OK'


@flat_api.route('/v1/devices/<int:device_id>/shutdown', methods=['POST'])
def shutdown(device_id: int):
    """Enqueues a Shutdown command for the device id specified.

    :reqheader Accept: application/json
    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :statuscode 201: command created
    :statuscode 400: not applicable to this device
    :statuscode 404: device with this identifier was not found
    :statuscode 500: system error
    """
    d = db.session.query(Device).filter(Device.id == device_id).one()

    if d.model_name == 'iPhone' and not d.is_supervised:
        return 'Cannot shut down an unsupervised iOS device', 400, {}

    cmd = commands.ShutDownDevice()
    orm_cmd = Command.from_model(cmd)
    orm_cmd.device = d
    db.session.add(orm_cmd)

    db.session.commit()

    return 'OK'


@flat_api.route('/v1/upload/profiles', methods=['POST'])
def upload_profile():
    """Upload a custom profile using multipart/form-data I.E from an upload input.

    Encrypted profiles are not supported.

    The profiles contents will be stored using the following process:
    - For the top level profile (and each payload) there is a marshmallow schema which maps the payload keys into
        the SQLAlchemy model keys. It is also the responsibility of the marshmallow schema to be the validator for 
        uploaded profiles.
    - The profile itself is inserted as a Profile model.
    - Each payload is unmarshalled using marshmallow to a specific Payload model. Each specific model contains a join
        table inheritance to the base ``payloads`` table.

    The returned body contains a jsonapi object with details of the newly created profile and associated payload ID's.

    Note: Does not support ``application/x-www-form-urlencoded``

    TODO:
        - Support signed profiles

    :reqheader Accept: application/vnd.api+json
    :reqheader Content-Type: multipart/form-data
    :resheader Content-Type: application/vnd.api+json
    :statuscode 201: profile created
    :statuscode 400: If the request contained malformed or missing payload data.
    :statuscode 500: If something else went wrong with parsing or persisting the payload(s)
    """
    if 'file' not in request.files:
        abort(400, 'no file uploaded in request data')

    f = request.files['file']

    if f.content_type != 'application/x-apple-aspen-config':
        abort(400, 'incorrect MIME type in request')

    try:
        data = f.read()
        plist = plistlib.loads(data)

        profile = ProfilePlistSchema().load(plist).data
    except plistlib.InvalidFileException as e:
        current_app.logger.error(e)
        abort(400, 'invalid plist format supplied')

    except BaseException as e:  # TODO: separate errors for exceptions caught here
        current_app.logger.error(e)
        abort(400, 'cannot parse the supplied profile')

    profile.data = data
    db.session.add(profile)
    db.session.commit()

    profile_schema = ProfileSchema()
    model_data = profile_schema.dump(profile).data
    return make_response(
        jsonify(model_data), 201, {'Content-Type': 'application/vnd.api+json'}
    )


@flat_api.route('/v1/download/profiles/<int:profile_id>')
def download_profile(profile_id: int):
    """Download a profile.
    
    The profile is reconstructed from its database representation.
    
    Args:
        profile_id (int): The profile id 

    :reqheader Accept: application/x-apple-aspen-config
    :resheader Content-Type: application/x-apple-aspen-config
    :statuscode 200:
    :statuscode 404:
    :statuscode 500:
    """
    try:
        profile = db.session.query(Profile).filter(Profile.id == profile_id).one()
    except NoResultFound:
        abort(404)

    return profile.data, 200, {'Content-Type': 'application/x-apple-aspen-config'}

