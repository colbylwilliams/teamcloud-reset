import logging
import typing
import json

import azure.functions as func

from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.resource.resources.aio import ResourceManagementClient
from azure.mgmt.resource.subscriptions.models import Subscription


async def main(msg: func.QueueMessage, msgs: func.Out[typing.List[str]]) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))

    sub = Subscription.deserialize(msg.get_json())

    logging.info('Reseting subscription: %s (%s)', sub.display_name, sub.subscription_id)

    credential = DefaultAzureCredential(logging_enable=True)
    client = ResourceManagementClient(credential=credential, subscription_id=sub.subscription_id)

    async with client, credential:
        rgs = await client.resource_groups.list()

    logging.info('Deleting the following Resource Groups:')

    for rg in rgs:
        logging.info('...%s (%s)', rg.name, rg.id)

    rg_msgs = [json.dumps(rg.serialize(keep_readonly=True)) for rg in rgs]

    msgs.set(rg_msgs)

    logging.info('Done.')
