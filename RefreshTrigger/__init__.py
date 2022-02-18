import os
import datetime
import logging
import typing
import json

import azure.functions as func

from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.resource.subscriptions.aio import SubscriptionClient


async def main(refreshtimer: func.TimerRequest, msgs: func.Out[typing.List[str]]) -> None:

    # Cron set to "0 0 5 * * 1" Monday morning 5am UTC

    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    if refreshtimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Refresh trigger function ran at %s', utc_timestamp)

    svc_sub_id = os.environ['TEAMCLOUD_SVC_SUBSCRIPTION']
    sub_prefix = os.environ['SUBSCRIPTION_FILTER_PREFIX']

    credential = DefaultAzureCredential()

    sub_msgs = []

    logging.info('Queuing purge of soft-deleted KeyVaults in the following subscriptions:')

    async with credential, SubscriptionClient(credential=credential) as client:
        async for sub in client.subscriptions.list():
            if sub.display_name.lower().startswith(sub_prefix) and not sub.subscription_id == svc_sub_id:
                logging.info('...%s (%s)', sub.display_name, sub.subscription_id)
                sub_msgs.append(json.dumps(sub.serialize(keep_readonly=True)))

    msgs.set(sub_msgs)

    logging.info('Done.')
