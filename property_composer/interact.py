from __future__ import annotations

from typing import Any

import requests

from .config import interact_settings


class InteractClient:
    def __init__(self) -> None:
        settings = interact_settings()
        self.api_domain = settings["api_domain"]
        self.tenant_guid = settings["tenant_guid"]
        self.api_key = settings["api_key"]
        self.api_secret = settings["api_secret"]
        self.person_id = settings["person_id"]
        self.session = requests.Session()
        self._token: str | None = None

    def authenticate(self) -> str:
        response = self.session.post(
            f"{self.api_domain}/token",
            params={"personid": self.person_id},
            headers={
                "X-Tenant": self.tenant_guid,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": f"{self.api_key}__{self.api_secret}",
                "context": "KeySecret",
            },
            timeout=30,
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("Interact token response did not include access_token")
        self._token = token
        return token

    def _headers(self) -> dict[str, str]:
        token = self._token or self.authenticate()
        return {
            "X-Tenant": self.tenant_guid,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    def get_page(self, page_id: int | str) -> dict[str, Any]:
        response = self.session.get(
            f"{self.api_domain}/api/page/{page_id}/composer/latest",
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def create_html_page(
        self,
        *,
        title: str,
        summary: str,
        html: str,
        category_ids: list[int],
        top_section_ids: list[int],
        keywords: list[str] | None = None,
        message: str = "Created by Property Details Page Composer",
    ) -> dict[str, Any]:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        payload = {
            "Transition": {
                "State": "Published",
                "Message": message,
                "SendNotifications": False,
                "ResendMentions": False,
            },
            "Page": {
                "AuthorId": int(self.person_id),
                "PublishAsId": int(self.person_id),
                "PublisherType": 0,
                "CategoryIds": category_ids,
                "TopSectionIds": top_section_ids,
                "TagIds": [],
                "Keywords": keywords or [],
                "ContentType": "html",
                "Title": title,
                "Summary": summary,
                "Content": {"Html": html},
                "Features": {
                    "DefaultToFullWidth": True,
                    "AllowComments": False,
                    "IsKeyPage": False,
                    "Recommends": {"Show": False, "MaxContentAge": 7},
                    "IsMandatoryRead": False,
                    "ShowTimeToRead": False,
                    "ShowPublishedDate": False,
                    "ShowUpdatedDate": False,
                },
                "Audience": {
                    "RelatedContent": [],
                    "NotificationRecipients": [],
                },
                "PubStartDate": now.isoformat(),
                "PubEndDate": (now + timedelta(days=3650)).isoformat(),
                "ReviewDate": (now + timedelta(days=365)).isoformat(),
                "IsPublic": False,
                "IsDiscoverable": True,
                "IsBlockEditorPage": False,
            },
        }

        headers = self._headers() | {"Content-Type": "application/json"}
        response = self.session.post(
            f"{self.api_domain}/api/page/composer",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _tag_ids(page: dict[str, Any]) -> list[Any]:
        values = []
        for tag in page.get("Tags", []):
            if isinstance(tag, dict):
                value = tag.get("TagId", tag.get("Id"))
                if value is not None:
                    values.append(value)
        return values

    @staticmethod
    def _keywords(page: dict[str, Any]) -> list[str]:
        values = []
        for keyword in page.get("Keywords", []):
            if isinstance(keyword, str):
                values.append(keyword)
            elif isinstance(keyword, dict):
                value = keyword.get("Value") or keyword.get("value")
                if value:
                    values.append(value)
        return values

    def update_html_page(
        self,
        page_id: int | str,
        html: str,
        *,
        title: str | None = None,
        summary: str | None = None,
        message: str = "Property Details Page Composer update",
    ) -> dict[str, Any]:
        current = self.get_page(page_id)

        if current.get("IsBlockEditorPage"):
            raise RuntimeError(
                f"Interact page {page_id} is a Block Editor page. "
                "Use a pure HTML Page Composer page as the publish target."
            )

        page_payload: dict[str, Any] = {
            "AuthorId": current["Author"]["Id"],
            "PublishAsId": current["PublishedAs"]["Id"],
            "PublisherType": current["PublishedAs"].get("PublisherType", 0),
            "CategoryIds": [item["Id"] for item in current.get("Categories", [])],
            "TagIds": self._tag_ids(current),
            "Keywords": self._keywords(current),
            "TopSectionIds": current.get("TopSectionIds", []),
            "AssetId": current["AssetId"],
            "ContentType": "html",
            "Title": title or current["Title"],
            "Summary": summary if summary is not None else current.get("Summary", ""),
            "Content": {"Html": html},
            "Features": current.get("Features", {}),
            "Audience": current.get("Audience", {
                "RelatedContent": [],
                "NotificationRecipients": [],
            }),
            "PubStartDate": current.get("PubStartDate"),
            "PubEndDate": current.get("PubEndDate"),
            "ReviewDate": current.get("ReviewDate"),
            "ConfidentialityId": current.get("ConfidentialityId"),
            "ClassificationId": current.get("ClassificationId"),
            "BestBets": current.get("BestBets", []),
            "IsPublic": current.get("IsPublic", False),
            "IsDiscoverable": current.get("IsDiscoverable", True),
            "HasPublicationDateBeenSet": current.get("HasPublicationDateBeenSet", False),
            "IsBlockEditorPage": False,
        }

        page_payload = {key: value for key, value in page_payload.items() if value is not None}

        payload = {
            "Transition": {
                "State": "Published",
                "Message": message,
                "SendNotifications": False,
                "ResendMentions": False,
            },
            "Page": page_payload,
        }

        headers = self._headers() | {"Content-Type": "application/json"}
        response = self.session.put(
            f"{self.api_domain}/api/page/{page_id}/composer",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
