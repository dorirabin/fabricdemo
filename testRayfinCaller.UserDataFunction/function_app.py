import datetime
import fabric.functions as fn
import logging

udf = fn.UserDataFunctions()

@udf.context(argName="udfContext")
@udf.function()
def testRayfinCaller(
    udfContext: fn.UserDataFunctionContext,
    vesselName: str = ""
) -> dict:
    logging.info("testRayfinCaller invoked")

    user = udfContext.executing_user

    return {
        "success": True,
        "invocationId": udfContext.invocation_id,
        "executingUser": {
            "oid": user.get("Oid"),
            "tenantId": user.get("TenantId"),
            "preferredUsername": user.get("PreferredUsername"),
        },
        "vesselName": vesselName,
        "serverTimeUtc": datetime.datetime.utcnow().isoformat() + "Z",
        "message": "UDF was invoked successfully with a verified Fabric/Entra identity."
    }
