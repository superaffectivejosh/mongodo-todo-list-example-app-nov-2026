"""Load secrets on the server; never return the connection URI to the browser."""

from urllib.parse import parse_qsl, quote_plus, unquote, urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    mongodb_uri: SecretStr
    mongodb_username: SecretStr | None = None
    mongodb_password: SecretStr | None = None
    mongodb_database: str | None = None

    @field_validator("mongodb_uri")
    @classmethod
    def validate_mongodb_uri(cls, value: SecretStr) -> SecretStr:
        uri = value.get_secret_value()
        if not uri.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("Use a mongodb:// or mongodb+srv:// URI.")
        unsafe = {"tlsinsecure", "tlsallowinvalidcertificates", "tlsallowinvalidhostnames"}
        query = uri.partition("?")[2]
        if any(key.lower() in unsafe for key, _ in parse_qsl(query.replace(";", "&"))):
            raise ValueError("Remove TLS verification bypass options from the MongoDB URI.")
        return value

    @property
    def uri(self) -> str:
        uri = self.mongodb_uri.get_secret_value()
        # Support common Atlas template URIs as well as complete URIs.
        for key, value in (("username", self.mongodb_username), ("password", self.mongodb_password)):
            if value:
                for token in (f"<{key}>", "{" + key + "}", f"<db_{key}>"):
                    uri = uri.replace(token, quote_plus(value.get_secret_value()))
        return uri

    @property
    def database_name(self) -> str:
        return self.mongodb_database or unquote(urlsplit(self.uri).path.lstrip("/")) or "little_wins"
