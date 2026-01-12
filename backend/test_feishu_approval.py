"""Unit tests for Feishu approval manager core interactions."""
import json
from unittest.mock import Mock, patch

import pytest

from feishu_approval import FeishuApprovalManager, ApprovalAPIError


@pytest.fixture
def mock_token() -> str:
    """Provide a mocked tenant access token."""
    return "mock_tenant_access_token"


@pytest.fixture
def approval_manager(mock_token: str) -> FeishuApprovalManager:
    """Create a FeishuApprovalManager instance wired to the mocked token provider."""
    with patch("feishu_approval.FeishuBitableReader") as MockReader:
        reader_instance = Mock()
        reader_instance._get_tenant_access_token.return_value = mock_token
        MockReader.return_value = reader_instance
        manager = FeishuApprovalManager(
            app_id="test_app_id",
            app_secret="test_secret",
            approval_code="test_approval_code",
        )
    return manager


def test_get_tenant_access_token_success(approval_manager: FeishuApprovalManager, mock_token: str) -> None:
    """Ensure get_tenant_access_token returns the mocked token from the provider."""
    token = approval_manager.get_tenant_access_token()

    assert token == mock_token
    approval_manager._token_provider._get_tenant_access_token.assert_called_once()


@patch("feishu_approval.requests.request")
def test_create_instance_success(mock_request: Mock, approval_manager: FeishuApprovalManager, mock_token: str) -> None:
    """Verify create_instance issues the correct payload and returns the instance code."""
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {
        "code": 0,
        "msg": "success",
        "data": {
            "instance_code": "oc-approval-123",
        },
    }
    mock_request.return_value = mock_response

    form_data = {"text_1": {"value": "Launch campaign"}}
    instance_code = approval_manager.create_instance(
        user_id="user_123",
        form_data=form_data,
        uuid="uuid-123",
    )

    assert instance_code == "oc-approval-123"
    mock_request.assert_called_once()
    call_kwargs = mock_request.call_args.kwargs
    assert call_kwargs["method"] == "POST"
    assert call_kwargs["url"] == f"{approval_manager.API_BASE_URL}/instances"
    assert call_kwargs["headers"]["Authorization"] == f"Bearer {mock_token}"
    assert call_kwargs["json"]["approval_code"] == "test_approval_code"
    assert call_kwargs["json"]["user_id"] == "user_123"
    assert call_kwargs["json"]["uuid"] == "uuid-123"
    assert json.loads(call_kwargs["json"]["form"]) == form_data


@patch("feishu_approval.requests.request")
def test_create_instance_api_error(mock_request: Mock, approval_manager: FeishuApprovalManager) -> None:
    """Ensure create_instance raises ApprovalAPIError when Feishu reports an error."""
    error_payload = {
        "code": 10002,
        "msg": "invalid arguments",
        "data": {"details": "field text_1 missing"},
    }
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = error_payload
    mock_request.return_value = mock_response

    with pytest.raises(ApprovalAPIError) as exc:
        approval_manager.create_instance(
            user_id="user_123",
            form_data={"text_2": {"value": "Missing required field"}},
            uuid="uuid-456",
        )

    assert exc.value.payload == error_payload
    assert "invalid arguments" in str(exc.value)
    mock_request.assert_called_once()


@patch("feishu_approval.requests.request")
def test_cancel_instance_success(mock_request: Mock, approval_manager: FeishuApprovalManager, mock_token: str) -> None:
    """Confirm cancel_instance sends the cancel request and reports success."""
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {"code": 0, "msg": "success", "data": {}}
    mock_request.return_value = mock_response

    result = approval_manager.cancel_instance(instance_code="oc-approval-123", user_id="user_123")

    assert result is True
    mock_request.assert_called_once()
    call_kwargs = mock_request.call_args.kwargs
    assert call_kwargs["method"] == "POST"
    assert call_kwargs["url"] == f"{approval_manager.API_BASE_URL}/instances/cancel"
    assert call_kwargs["params"] == {"user_id_type": approval_manager.user_id_type}
    assert call_kwargs["headers"]["Authorization"] == f"Bearer {mock_token}"
    assert call_kwargs["json"]["instance_code"] == "oc-approval-123"
    assert call_kwargs["json"]["user_id"] == "user_123"


@patch("feishu_approval.requests.request")
def test_get_instance_detail_success(mock_request: Mock, approval_manager: FeishuApprovalManager, mock_token: str) -> None:
    """Validate get_instance_detail returns the parsed instance detail data."""
    detail_payload = {
        "instance_code": "oc-approval-123",
        "status": "PENDING",
        "form": {"text_1": {"value": "Launch campaign"}},
    }
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {
        "code": 0,
        "msg": "success",
        "data": {"instance": detail_payload},
    }
    mock_request.return_value = mock_response

    data = approval_manager.get_instance_detail(instance_code="oc-approval-123")

    assert data == {"instance": detail_payload}
    mock_request.assert_called_once()
    call_kwargs = mock_request.call_args.kwargs
    assert call_kwargs["method"] == "GET"
    assert call_kwargs["url"] == f"{approval_manager.API_BASE_URL}/instances/oc-approval-123"
    assert call_kwargs["params"] == {"user_id_type": approval_manager.user_id_type}
    assert call_kwargs["headers"]["Authorization"] == f"Bearer {mock_token}"
    assert call_kwargs.get("json") is None


@patch("feishu_approval.requests.request")
def test_cc_instance_success(mock_request: Mock, approval_manager: FeishuApprovalManager, mock_token: str) -> None:
    """Check cc_instance forwards cc users and comment to the API."""
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {"code": 0, "msg": "success", "data": {}}
    mock_request.return_value = mock_response

    cc_user_ids = ["user_123", "user_456"]
    result = approval_manager.cc_instance(
        instance_code="oc-approval-123",
        cc_user_ids=cc_user_ids,
        comment="FYI on the latest approval",
    )

    assert result is True
    mock_request.assert_called_once()
    call_kwargs = mock_request.call_args.kwargs
    assert call_kwargs["method"] == "POST"
    assert call_kwargs["url"] == f"{approval_manager.API_BASE_URL}/instances/cc"
    assert call_kwargs["params"] == {"user_id_type": approval_manager.user_id_type}
    assert call_kwargs["headers"]["Authorization"] == f"Bearer {mock_token}"
    assert call_kwargs["json"]["cc_user_ids"] == cc_user_ids
    assert call_kwargs["json"]["comment"] == "FYI on the latest approval"
    assert call_kwargs["json"]["approval_code"] == "test_approval_code"
    assert call_kwargs["json"]["instance_code"] == "oc-approval-123"
