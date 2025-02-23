import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from azure.cosmos import CosmosClient, exceptions


class NebulaUserDB:
    def __init__(
        self,
        connection_string: str,
        database_id: str = "nebula-db",
        container_id: str = "users",
    ):
        """Initialize UserDB with Azure Cosmos DB connection."""
        self.client = CosmosClient.from_connection_string(connection_string)
        self.database = self.client.get_database_client(database_id)
        self.container = self.database.get_container_client(container_id)

    def create_user(self, username: str, additional_data: Dict = None) -> Dict:
        """Create a new user in the database."""
        timestamp = datetime.now(timezone.utc)

        user_doc = {
            "id": str(uuid.uuid4()),
            "type": "user",
            "username": username.lower(),
            "profile": {
                "created_at": timestamp.isoformat(),
                "last_modified": timestamp.isoformat(),
                "is_active": True,
            },
            "metadata": {"last_login": None, "login_count": 0},
            "settings": {},  # User preferences/settings
            "stats": {},  # User statistics/metrics
        }

        # Additional data can go into appropriate nested objects
        if additional_data:
            for key, value in additional_data.items():
                # Example: if key is "settings.theme", it goes into settings
                if "." in key:
                    parent, child = key.split(".", 1)
                    if parent not in user_doc:
                        user_doc[parent] = {}
                    user_doc[parent][child] = value
                else:
                    # Direct field or new nested object
                    user_doc[key] = value

        try:
            return self.container.create_item(user_doc)
        except exceptions.CosmosResourceExistsError:
            raise ValueError(f"User with username {username} already exists")

    def get_user(self, username: str, fields: List[str] = None) -> Optional[Dict]:
        """
        Retrieve a user by username.
        Optionally specify fields to return specific data only.
        """
        select_clause = "*" if not fields else ", ".join(fields)
        query = f"SELECT {select_clause} FROM c WHERE c.username = @username AND c.type = 'user'"
        parameters = [{"name": "@username", "value": username.lower()}]

        results = list(
            self.container.query_items(
                query=query, parameters=parameters, enable_cross_partition_query=True
            )
        )
        return results[0] if results else None

    def update_user(self, username: str, update_data: Dict) -> Dict:
        """Update user information - supports nested updates."""
        user = self.get_user(username)
        if not user:
            raise ValueError(f"User {username} not found")

        # Handle nested updates
        for key, value in update_data.items():
            if "." in key:
                # Handle nested field updates (e.g., "profile.is_active")
                parent, child = key.split(".", 1)
                if parent not in user:
                    user[parent] = {}
                user[parent][child] = value
            else:
                user[key] = value

        # Update last modified timestamp
        user["profile"]["last_modified"] = datetime.now(timezone.utc).isoformat()

        return self.container.upsert_item(user)

    def list_users(self, query_spec: Dict = None) -> List[Dict]:
        """
        List users with flexible querying.
        query_spec can include filters, sorting, etc.
        """
        base_query = "SELECT * FROM c WHERE c.type = 'user'"

        if query_spec:
            conditions = []
            parameters = []

            for field, value in query_spec.get("filters", {}).items():
                param_name = f"@{field.replace('.', '_')}"
                conditions.append(f"c.{field} = {param_name}")
                parameters.append({"name": param_name, "value": value})

            if conditions:
                base_query += f" AND {' AND '.join(conditions)}"

            if "order_by" in query_spec:
                base_query += f" ORDER BY c.{query_spec['order_by']}"

            users = self.container.query_items(
                query=base_query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        else:
            users = self.container.query_items(
                query=base_query, enable_cross_partition_query=True
            )

        return list(users)

    def deactivate_user(self, username: str) -> Dict:
        """Deactivate a user account."""
        return self.update_user(username, {"profile.is_active": False})

    def activate_user(self, username: str) -> Dict:
        """Activate a user account."""
        return self.update_user(username, {"profile.is_active": True})

    def delete_user(self, username: str) -> None:
        """Delete a user from the database."""
        user = self.get_user(username)
        if not user:
            raise ValueError(f"User {username} not found")

        try:
            self.container.delete_item(item=user["id"], partition_key=username.lower())
        except exceptions.CosmosResourceNotFoundError:
            raise ValueError(f"User {username} not found")
