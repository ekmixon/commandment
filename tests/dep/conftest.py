import pytest
import requests
import os.path

from commandment.dep import SetupAssistantStep
from commandment.dep.dep import DEP
from commandment.dep.models import DEPProfile
from commandment.models import Device
from sqlalchemy.orm.session import Session

SIMULATOR_URL = 'http://localhost:8080'


@pytest.fixture
def simulator_token() -> dict:
    res = requests.get(f'{SIMULATOR_URL}/token')
    return res.json()


@pytest.fixture
def live_token() -> str:
    dep_token_path = os.path.join(os.path.dirname(__file__), '..', '..', 'testdata', 'deptoken.json')
    with open(dep_token_path, 'rb') as fd:
        content = fd.read()

    return content.decode('utf8')


@pytest.fixture
def live_device() -> str:
    return os.environ.get('DEP_DEVICE_UUID')


@pytest.fixture
def live_dep_profile() -> str:
    return os.environ.get('DEP_PROFILE_UUID')


@pytest.fixture
def dep(simulator_token: dict) -> DEP:
    return DEP(
        consumer_key=simulator_token['consumer_key'],
        consumer_secret=simulator_token['consumer_secret'],
        access_token=simulator_token['access_token'],
        access_secret=simulator_token['access_secret'],
        url=SIMULATOR_URL,
    )


@pytest.fixture
def dep_live(live_token: str):
    return DEP.from_token(live_token)


@pytest.fixture
def dep_profile() -> dict:
    return {
        'profile_name': 'Fixture Profile',
        'url': 'https://localhost:5433',
        'allow_pairing': True,
        'is_supervised': True,
        'is_multi_user': False,
        'is_mandatory': False,
        'await_device_configured': False,
        'is_mdm_removable': True,
        'support_phone_number': '12345678',
        'auto_advance_setup': False,
        'support_email_address': 'test@localhost',
        'org_magic': 'COMMANDMENT-TEST-FIXTURE',
        'skip_setup_items': [
            SetupAssistantStep.AppleID,
        ],
        'department': 'Commandment Dept',
        'devices': [],
    }


@pytest.fixture
def dep_profile_committed(dep_profile: dict, session: Session):
    dp = DEPProfile(**dep_profile)
    session.add(dp)
    session.commit()


@pytest.fixture(scope='function')
def device(session: Session):
    """Create a fixture device which is referenced in all of the fake MDM responses by its UDID."""
    d = Device(
        udid='00000000-1111-2222-3333-444455556666',
        device_name='commandment-mdmclient'
    )
    session.add(d)
    session.commit()
