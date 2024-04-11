import base64
import kopf
import kubernetes
import uuid

from mailersend import emails

email_configs = {}


def get_token_secret(provider):
    """Get Enocoded token secret based on provider name and return decoded api token"""

    core_api = kubernetes.client.CoreV1Api()

    try:
        secret = core_api.read_namespaced_secret(
            name="token-secret", namespace="default"
        )
        match provider:
            case "mailersend":
                token_bytes = base64.b64decode(secret.data["MAILERSEND_API_TOKEN"])
            case "mailgun":
                token_bytes = base64.b64decode(secret.data["MAILGUN_API_TOKEN"])
            case _:
                raise ValueError(f"Unknow provider Name")
        return token_bytes.decode("ascii")
    except kubernetes.client.rest.ApiException as e:
        if e.status == 404:
            raise ValueError(f"Secret 'token-secret' not found in namespace 'default'")
        else:
            raise RuntimeError(f"Error retrieving Secret 'token-secret': {e}")


def fetch_exist_email_sender_configs():
    """Fetch exist emial confings"""

    api = kubernetes.client.CustomObjectsApi()
    (exist_email_sender_configs, _, _) = (
        api.list_namespaced_custom_object_with_http_info(
            group="mailerlite.com",
            version="v1",
            namespace="default",
            plural="emailsenderconfigs",
        )
    )
    for item in exist_email_sender_configs["items"]:
        provider = item["spec"]["provider"]
        senderEmail = item["spec"]["senderEmail"]
        api_token = get_token_secret(provider)
        email_sender_config_name = item["metadata"]["name"]

        email_configs.update(
            {
                email_sender_config_name: {
                    "apiToken": api_token,
                    "provider": provider,
                    "senderEmail": senderEmail,
                }
            }
        )


@kopf.on.create("EmailSenderConfig")
@kopf.on.update("EmailSenderConfig")
def handle_email_sender_config(body, **kwargs):
    """Add or update email configs"""

    provider = body.spec["provider"]
    email_sender_config_name = body["metadata"]["name"]

    api_token = get_token_secret(provider)

    email_configs.update(
        {
            email_sender_config_name: {
                "apiToken": api_token,
                "provider": provider,
                "senderEmail": body.spec["senderEmail"],
            }
        }
    )


@kopf.on.create("Email")
@kopf.on.update("Email")
def create_fn(body, **kwargs):
    """Send email based on provider for newly create or updated emial"""
    api = kubernetes.client.CustomObjectsApi()

    email_sender_config_name = body.spec["senderConfigRef"]
    email_name = body["metadata"]["name"]

    if not email_configs:
        fetch_exist_email_sender_configs()

    email_config = email_configs.get(email_sender_config_name)

    if not email_config:
        raise ValueError(
            f"Email Sender Config '{email_sender_config_name}' not found for '{email_name}' email"
        )

    match email_config["provider"]:
        case "mailersend":
            mailer = emails.NewEmail(email_config["apiToken"])
            mail_body = {}
            message_id = ""
            delivery_status = ""
            mail_from = {
                "email": email_config["senderEmail"],
            }
            recipients = [
                {
                    "email": body.spec["recipientEmail"],
                }
            ]
            mailer.set_mail_from(mail_from, mail_body)
            mailer.set_mail_to(recipients, mail_body)
            mailer.set_subject(body.spec["subject"], mail_body)
            mailer.set_plaintext_content(body.spec["body"], mail_body)
            try:
                response = mailer.send(mail_body)
                delivery_status = "Delivered"
                message_id = str(uuid.uuid4())
            except Exception as e:
                delivery_status = "Failed"
                message_id = str(uuid.uuid4())
        case "mailgun":
            # Here we can add mailgun provider configuration
            pass
        case _:
            raise ValueError(f"Unknow provider Name")

    email_status = {
        "status": {"deliveryStatus": delivery_status, "messageId": message_id}
    }
    api.patch_namespaced_custom_object(
        group="mailerlite.com",
        version="v1",
        namespace="default",
        plural="emails",
        name=email_name,
        body=email_status,
    )
