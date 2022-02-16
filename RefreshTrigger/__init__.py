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

    logging.info('Refresh trigger function ran at %s', utc_timestamp)

    sub_prefix = os.environ['SUBSCRIPTION_FILTER_PREFIX']
    skip_suffix = os.environ['SUBSCRIPTION_SKIP_SUFFIX']

    credential = DefaultAzureCredential()
    client = SubscriptionClient(credential=credential)

    logging.info('Queuing purge of soft-deleted KeyVaults in the following subscriptions:')

    sub_msgs = []

    async with client, credential:
        async for sub in client.subscriptions.list():
            if sub.display_name.lower().startswith(sub_prefix) and not sub.display_name.lower().endswith(skip_suffix):
                logging.info('...%s (%s)', sub.display_name, sub.subscription_id)
                sub_msgs.append(json.dumps(sub.serialize(keep_readonly=True)))

    msgs.set(sub_msgs)

    logging.info('Done.')
