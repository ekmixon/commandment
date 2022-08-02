from typing import Set
from enum import IntFlag, auto, Enum, IntEnum


class CommandType(Enum):
    ProfileList = 'ProfileList'
    InstallProfile = 'InstallProfile'
    RemoveProfile = 'RemoveProfile'
    ProvisioningProfileList = 'ProvisioningProfileList'
    InstallProvisioningProfile = 'InstallProvisioningProfile'
    RemoveProvisioningProfile = 'RemoveProvisioningProfile'
    CertificateList = 'CertificateList'
    InstalledApplicationList = 'InstalledApplicationList'
    DeviceInformation = 'DeviceInformation'
    SecurityInfo = 'SecurityInfo'
    DeviceLock = 'DeviceLock'
    RestartDevice = 'RestartDevice'
    ShutDownDevice = 'ShutDownDevice'
    ClearPasscode = 'ClearPasscode'
    EraseDevice = 'EraseDevice'
    RequestMirroring = 'RequestMirroring'
    StopMirroring = 'StopMirroring'
    Restrictions = 'Restrictions'
    ClearRestrictionsPasscode = 'ClearRestrictionsPasscode'

    # Shared iPad
    UserList = 'UserList'
    UnlockUserAccount = 'UnlockUserAccount'
    LogOutUser = 'LogOutUser'
    DeleteUser = 'DeleteUser'

    EnableLostMode = 'EnableLostMode'
    PlayLostModeSound = 'PlayLostModeSound'
    DisableLostMode = 'DisableLostMode'
    DeviceLocation = 'DeviceLocation'

    # Managed Applications
    InstallApplication = 'InstallApplication'
    ApplyRedemptionCode = 'ApplyRedemptionCode'
    ManagedApplicationList = 'ManageApplicationList'
    RemoveApplication = 'RemoveApplication'
    InviteToProgram = 'InviteToProgram'
    ValidateApplications = 'ValidateApplications'

    # Books
    InstallMedia = 'InstallMedia'
    ManagedMediaList = 'ManagedMediaList'
    RemoveMedia = 'RemoveMedia'

    Settings = 'Settings'

    ManagedApplicationConfiguration = 'ManagedApplicationConfiguration'
    ApplicationConfiguration = 'ApplicationConfiguration'
    ManagedApplicationAttributes = 'ManagedApplicationAttributes'
    ManagedApplicationFeedback = 'ManagedApplicationFeedback'
    AccountConfiguration = 'AccountConfiguration'

    SetFirmwarePassword = 'SetFirmwarePassword'
    VerifyFirmwarePassword = 'VerifyFirmwarePassword'

    SetAutoAdminPassword = 'SetAutoAdminPassword'
    DeviceConfigured = 'DeviceConfigured'
    ScheduleOSUpdate = 'ScheduleOSUpdate'
    ScheduleOSUpdateScan = 'ScheduleOSUpdateScan'
    AvailableOSUpdates = 'AvailableOSUpdates'
    OSUpdateStatus = 'OSUpdateStatus'

    ActiveNSExtensions = 'ActiveNSExtensions'
    NSExtensionMappings = 'NSExtensionMappings'
    RotateFileVaultKey = 'RotateFileVaultKey'


class Platform(Enum):
    """The platform of the managed device."""
    Unknown = 'Unknown'  # Not enough information
    macOS = 'macOS'
    iOS = 'iOS'
    tvOS = 'tvOS'


class AccessRights(IntFlag):
    """The MDM protocol defines a bitmask for granting permissions to an MDM to perform certain operations.
    
    This enumeration contains all of those access rights flags.
    """
    def _generate_next_value_(self, start, count, last_values):
        return 2 ** count

    ProfileInspection = auto()
    ProfileInstallRemove = auto()
    DeviceLockPasscodeRemoval = auto()
    DeviceErase = auto()
    QueryDeviceInformation = auto()
    QueryNetworkInformation = auto()
    ProvProfileInspection = auto()
    ProvProfileInstallRemove = auto()
    InstalledApplications = auto()
    RestrictionQueries = auto()
    SecurityQueries = auto()
    ChangeSettings = auto()
    ManageApps = auto()

    All = ProfileInspection | ProfileInstallRemove | DeviceLockPasscodeRemoval | DeviceErase | QueryDeviceInformation \
          | QueryNetworkInformation | ProvProfileInspection | ProvProfileInstallRemove | InstalledApplications \
          | RestrictionQueries | SecurityQueries | ChangeSettings | ManageApps


AccessRightsSet = Set[AccessRights]


class CommandStatus(Enum):
    """CommandStatus describes all the possible states of a command in the device command queue.

    The following statuses are based upon the return status of the MDM client:

    - Acknowledged
    - Error
    - CommandFormatError
    - NotNow

    Additionally, there are statuses to explain the lifecycle of the command before and after the MDM client processes
    them:

    - Queued: The command was newly created and not yet sent to the device.
    - Sent: The command has been sent to the device, but no response has come back yet.
    - Expired: The command was never acknowledged, or the device was removed.
    """

    # MDM Client Statuses
    Idle = 'Idle'
    Acknowledged = 'Acknowledged'
    Error = 'Error'
    CommandFormatError = 'CommandFormatError'
    NotNow = 'NotNow'

    # Commandment Lifecycle Statuses
    Queued = 'Queued'
    Sent = 'Sent'
    Expired = 'Expired'


class SettingsItem(Enum):
    """A list of possible values for Managed Settings items.

    See Also:
          - `Managed Settings <https://developer.apple.com/library/content/documentation/Miscellaneous/Reference/MobileDeviceManagementProtocolRef/3-MDM_Protocol/MDM_Protocol.html#//apple_ref/doc/uid/TP40017387-CH3-SW59>`_._
    """
    VoiceRoaming = 'VoiceRoaming'
    PersonalHotspot = 'PersonalHotspot'
    Wallpaper = 'Wallpaper'
    DataRoaming = 'DataRoaming'
    ApplicationAttributes = 'ApplicationAttributes'
    DeviceName = 'DeviceName'
    HostName = 'HostName'
    MDMOptions = 'MDMOptions'
    PasscodeLockGracePeriod = 'PasscodeLockGracePeriod'
    MaximumResidentUsers = 'MaximumResidentUsers'


class WallpaperLocation(IntEnum):
    """A list of possible values for the Wallpaper `where` setting.

    Determines where the given wallpaper will be used.
    """
    LockScreen = 1
    HomeScreen = 2
    Both = 3


