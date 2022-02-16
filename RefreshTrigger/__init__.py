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

    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if refreshtimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    sub_prefix = os.environ['SUBSCRIPTION_FILTER_PREFIX']
    skip_suffix = os.environ['SUBSCRIPTION_SKIP_SUFFIX']

    credential = DefaultAzureCredential(logging_enable=True)
    client = SubscriptionClient(credential=credential)

    async with client, credential:
        subs = [sub async for sub in client.subscriptions.list()
                if sub.display_name.lower().startswith(sub_prefix)
                and not sub.display_name.lower().endswith(skip_suffix)]

    logging.info('Purging KeyVaults in the following subscriptions:')

    for sub in subs:
        logging.info('...%s (%s)', sub.display_name, sub.subscription_id)

    sub_msgs = [json.dumps(sub.serialize(keep_readonly=True)) for sub in subs]

    msgs.set(sub_msgs)

    logging.info('Done.')
