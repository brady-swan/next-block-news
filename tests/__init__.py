"""Test safety barrier: no inherited credentials, autopost, or real network access."""
import atexit
import os
import shutil
import socket
import tempfile


SECRET_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "TYPEFULLY_API_KEY",
    "TYPEFULLY_SOCIAL_SET_ID",
    "NUELINK_API_KEY",
    "NUELINK_BRAND_ID",
    "NUELINK_COLLECTION_ID",
    "NBN_X_BEARER_TOKEN",
    "NBN_PERCEPTION_API_KEY",
    "NBN_NODE_READ_TOKEN",
    "NBN_REPORT_TOKEN",
    "NBN_HEARTBEAT_URL",
)

for _name in SECRET_ENV_VARS:
    os.environ.pop(_name, None)
# The Anthropic SDK validates presence at client construction time. A known dummy value
# lets modules import while the socket guard still makes any forgotten call fail loudly.
os.environ["ANTHROPIC_API_KEY"] = "test-not-a-real-key"
os.environ["NBN_AUTOPOST_ENABLED"] = "false"

_TEST_DATA_DIR = tempfile.mkdtemp(prefix="nbn-tests-")
os.environ["NBN_DATA_DIR"] = _TEST_DATA_DIR
atexit.register(shutil.rmtree, _TEST_DATA_DIR, ignore_errors=True)


def _blocked_network(*_args, **_kwargs):
    raise AssertionError("real network access is forbidden in tests")


socket.create_connection = _blocked_network
socket.socket.connect = _blocked_network
socket.socket.connect_ex = _blocked_network
