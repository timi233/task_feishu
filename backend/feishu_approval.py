"""Feishu approval API wrapper module."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import requests

from feishu_reader import FeishuBitableReader


logger = logging.getLogger(__name__)


class ApprovalAPIError(Exception):
    """Custom exception for Feishu approval API errors."""

    def __init__(self, message: str, *, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.payload: Dict[str, Any] = payload or {}

    def __str__(self) -> str:
        base_message = super().__str__()
        if not self.payload:
            return base_message
        return f"{base_message} | payload={self.payload}"


class FeishuApprovalManager:
    """Manager for interacting with Feishu native approval APIs."""

    API_BASE_URL = "https://open.feishu.cn/open-apis/approval/v4"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        approval_code: Optional[str] = None,
        *,
        user_id_type: str = "user_id",
        timeout: int = 15,
    ) -> None:
        """Initialize the manager with credentials and approval metadata."""
        if not app_id or not app_secret:
            raise ValueError("Feishu app_id and app_secret are required")

        self.app_id = app_id
        self.app_secret = app_secret
        self.approval_code = approval_code
        self.user_id_type = user_id_type
        self.timeout = timeout
        self._token_provider = FeishuBitableReader(app_id, app_secret, timeout=timeout)

    def _resolve_approval_code(self, override: Optional[str] = None) -> str:
        """Return the effective approval code, preferring the override when provided."""
        effective_code = override or self.approval_code
        if not effective_code:
            raise ValueError("approval_code is required for this operation")
        return effective_code

    def get_tenant_access_token(self) -> str:
        """Obtain tenant access token via the shared bitable reader logic."""
        token = self._token_provider._get_tenant_access_token()
        if not token:
            logger.error("Unable to obtain tenant_access_token")
            raise ApprovalAPIError("Failed to obtain tenant_access_token")
        return token

    def create_instance(
        self,
        user_id: str,
        form_data: Dict[str, Any],
        uuid: str,
        *,
        approval_code_override: Optional[str] = None,
    ) -> str:
        """Create a new approval instance and return its instance code."""
        if not user_id:
            raise ValueError("user_id is required")
        if not form_data:
            raise ValueError("form_data is required")
        if not uuid:
            raise ValueError("uuid is required")

        approval_code = self._resolve_approval_code(approval_code_override)
        payload = {
            "approval_code": approval_code,
            "user_id": user_id,
            "form": json.dumps(form_data, ensure_ascii=False),
            "uuid": uuid,
        }

        logger.info("Creating Feishu approval instance for user_id=%s", user_id)
        data = self._request("POST", "/instances", json=payload)
        instance_code = data.get("instance_code")
        if not instance_code:
            raise ApprovalAPIError("create_instance response missing instance_code", payload=data)
        logger.info("Approval instance created: %s", instance_code)
        return instance_code

    def cancel_instance(self, instance_code: str, user_id: str) -> bool:
        """Cancel an approval instance that was previously created."""
        if not instance_code:
            raise ValueError("instance_code is required")
        if not user_id:
            raise ValueError("user_id is required")

        approval_code = self._resolve_approval_code()
        payload = {
            "approval_code": approval_code,
            "instance_code": instance_code,
            "user_id": user_id,
        }

        logger.info("Canceling Feishu approval instance: %s", instance_code)
        self._request("POST", "/instances/cancel", params={"user_id_type": self.user_id_type}, json=payload)
        logger.info("Approval instance canceled: %s", instance_code)
        return True

    def get_instance_detail(self, instance_code: str) -> Dict[str, Any]:
        """Retrieve detail of an approval instance from Feishu."""
        if not instance_code:
            raise ValueError("instance_code is required")

        logger.info("Fetching approval instance detail: %s", instance_code)
        data = self._request(
            "GET",
            f"/instances/{instance_code}",
            params={"user_id_type": self.user_id_type},
        )
        logger.debug("Approval instance detail retrieved: %s", data)
        return data

    def cc_instance(self, instance_code: str, cc_user_ids: List[str], comment: str) -> bool:
        """CC users on an existing approval instance."""
        if not instance_code:
            raise ValueError("instance_code is required")
        if not cc_user_ids:
            raise ValueError("cc_user_ids must not be empty")

        approval_code = self._resolve_approval_code()
        payload = {
            "approval_code": approval_code,
            "instance_code": instance_code,
            "cc_user_ids": cc_user_ids,
            "comment": comment or "",
        }

        logger.info(
            "CCing approval instance %s to users=%s", instance_code, ",".join(cc_user_ids)
        )
        self._request("POST", "/instances/cc", params={"user_id_type": self.user_id_type}, json=payload)
        logger.info("Approval instance cc successful: %s", instance_code)
        return True

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Internal helper to execute HTTP requests with shared error handling."""
        token = self.get_tenant_access_token()
        url = f"{self.API_BASE_URL}{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        logger.debug(
            "Feishu approval API request: %s %s params=%s payload=%s",
            method,
            url,
            params,
            json,
        )

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("HTTP error during Feishu approval API call: %s %s", method, url)
            raise ApprovalAPIError(
                f"HTTP error during Feishu approval API call: {exc}"
            ) from exc

        try:
            result = response.json()
        except ValueError as exc:
            logger.exception("Failed to parse JSON response for %s %s", method, url)
            raise ApprovalAPIError("Invalid JSON response from Feishu approval API") from exc

        if result.get("code") != 0:
            logger.error(
                "Feishu approval API error for %s %s: %s",
                method,
                url,
                result,
            )
            raise ApprovalAPIError(
                f"Feishu approval API error: {result.get('msg', 'unknown error')}",
                payload=result,
            )

        data = result.get("data", {})
        logger.debug("Feishu approval API response data: %s", data)
        return data
