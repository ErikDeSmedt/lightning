import json
from pathlib import Path
from importlib import resources
from msggen.model import Method, CompositeField, Service, Notification, TypeName
import functools
from collections import OrderedDict


def combine_schemas(schema_dir: Path, dest: Path):
    """Enumerate all schema files, and combine it into a single JSON file."""
    bundle = OrderedDict()
    methods = OrderedDict()
    notifications = OrderedDict()

    # Parse methods
    files = sorted(list(schema_dir.iterdir()))
    for f in files:
        # Ignore lightning-sql.json because it will be auto generated by sql plugin and lightning-sql-template.json
        if not f.name.endswith(".json") or f.name == "lightning-sql.json":
            continue
        methods[f.name] = json.load(f.open())

    # Parse notifications
    notifications_dir = schema_dir / "notification"
    files = sorted(list(notifications_dir.iterdir()))
    for f in files:
        if not f.name.endswith("json"):
            continue
        notifications[f.name] = json.load(f.open())

    bundle["methods"] = methods
    bundle["notifications"] = notifications

    with dest.open(mode='w') as f:
        json.dump(
            bundle,
            f,
            indent=2,
        )
    return bundle


@functools.lru_cache(maxsize=1)
def get_schema_bundle():
    """Load the schema bundle from the combined schema file.

    The combined schema is generated by `combine_schemas`.
    """
    p = resources.open_text("msggen", "schema.json")
    return json.load(p)


def load_jsonrpc_method(name):
    """Load a method based on the file naming conventions for the JSON-RPC.
    """
    schema = get_schema_bundle()
    rpc_name = f"lightning-{name.lower()}.json"
    request = CompositeField.from_js(schema["methods"][rpc_name]['request'], path=name)
    response = CompositeField.from_js(schema["methods"][rpc_name]['response'], path=name)

    # Normalize the method request and response typename so they no
    # longer conflict.
    request.typename += "Request"
    response.typename += "Response"

    return Method(
        name,
        request=request,
        response=response,
    )


def load_notification(name, typename: TypeName):
    """Load a notification that can be received by a plug-in
    """
    typename = str(typename)

    schema = get_schema_bundle()
    notifications = schema["notifications"]
    req_file = f"{name.lower()}.request.json"
    resp_file = f"{name.lower()}.schema.json"
    request = CompositeField.from_js(notifications[req_file], path=name)
    response = CompositeField.from_js(notifications[resp_file], path=name)

    request.typename = TypeName(f"Stream{typename}Request")
    response.typename = TypeName(f"{typename}Notification")

    return Notification(name, TypeName(typename), request, response)


def load_jsonrpc_service():
    method_names = [
        "Getinfo",
        "ListPeers",
        "ListFunds",
        "SendPay",
        "ListChannels",
        "AddGossip",
        "AutoCleanInvoice",
        "AutoClean-Once",
        "AutoClean-Status",
        "CheckMessage",
        "Close",
        "Connect",
        "CreateInvoice",
        "Datastore",
        "DatastoreUsage",
        "CreateOnion",
        "DelDatastore",
        "DelInvoice",
        "Invoice",
        "ListDatastore",
        "ListInvoices",
        "SendOnion",
        "ListSendPays",
        "ListTransactions",
        "Pay",
        "ListNodes",
        "WaitAnyInvoice",
        "WaitInvoice",
        "WaitSendPay",
        "NewAddr",
        "Withdraw",
        "KeySend",
        "FundPsbt",
        "SendPsbt",
        "SignPsbt",
        "UtxoPsbt",
        "TxDiscard",
        "TxPrepare",
        "TxSend",
        "ListPeerChannels",
        "ListClosedChannels",
        "DecodePay",
        "Decode",
        "DelPay",
        "DelForward",
        "DisableOffer",
        "Disconnect",
        "Feerates",
        "FetchInvoice",
        "FundChannel_Cancel",
        "FundChannel_Complete",
        "FundChannel",
        "FundChannel_Start",
        # "funderupdate",
        "GetLog",
        "GetRoute",
        "ListForwards",
        "ListOffers",
        "ListPays",
        "ListHtlcs",
        "MultiFundChannel",
        # "multiwithdraw",
        "Offer",
        "OpenChannel_Abort",
        "OpenChannel_Bump",
        "OpenChannel_Init",
        "OpenChannel_Signed",
        "OpenChannel_Update",
        # "parsefeerate",
        "Ping",
        "Plugin",
        "RenePayStatus",
        "RenePay",
        "ReserveInputs",
        "SendCustomMsg",
        "SendInvoice",
        "SendOnionMessage",
        "SetChannel",
        "SetConfig",
        "SetPsbtVersion",
        "SignInvoice",
        "SignMessage",
        "Splice_Init",
        "Splice_Signed",
        "Splice_Update",
        "UnreserveInputs",
        "UpgradeWallet",
        "WaitBlockHeight",
        "Wait",
        # "ListConfigs",
        # "check",  # No point in mapping this one
        "Stop",
        # "notifications",  # No point in mapping this
        # "help",
        "PreApproveKeysend",
        "PreApproveInvoice",
        "StaticBackup",
        "Bkpr-ChannelsApy",
        "Bkpr-DumpIncomeCsv",
        "Bkpr-Inspect",
        "Bkpr-ListAccountEvents",
        "Bkpr-ListBalances",
        "Bkpr-ListIncome",
    ]

    notification_names = [
        {
            "name": "block_added",
            "typename": "BlockAdded"
        },
        {
            "name": "channel_open_failed",
            "typename": "ChannelOpenFailed"
        },
        {
            "name": "channel_opened",
            "typename": "ChannelOpened"
        },
        {
            "name": "connect",
            "typename": "Connect"
        },
        {
            "name": "custommsg",
            "typename": "CustomMsg"
        },
    ]

    methods = [load_jsonrpc_method(name) for name in method_names]
    notifications = [load_notification(name=names["name"], typename=names["typename"]) for names in notification_names]
    service = Service(name="Node", methods=methods, notifications=notifications)
    service.includes = ['primitives.proto']  # Make sure we have the primitives included.
    return service
