import pytest

def pytest_addoption(parser):
    parser.addoption("--customer_code", action="store", default="")
    parser.addoption("--customer_password", action="store", default="")
    parser.addoption("--customer_cls_cocde", action="store", default="")
    parser.addoption("--login_user_id", action="store", default="")
    parser.addoption("--addressian_api_key", action="store", default="")


@pytest.fixture
def customer_code(request):
    return request.config.getoption("--customer_code")


@pytest.fixture
def customer_password(request):
    return request.config.getoption("--customer_password")


@pytest.fixture
def customer_cls_cocde(request):
    return request.config.getoption("--customer_cls_cocde")


@pytest.fixture
def login_user_id(request):
    return request.config.getoption("--login_user_id")


@pytest.fixture
def addressian_api_key(request):
    return request.config.getoption("--addressian_api_key")