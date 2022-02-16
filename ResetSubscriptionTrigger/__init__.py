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

    logging.info('Reseting subscription: %s', sub.display_name)

    credential = DefaultAzureCredential()
    client = ResourceManagementClient(credential=credential, subscription_id=sub.subscription_id)

    logging.info('Queuing delete of the following Resource Groups:')

    rg_msgs = []

    async with client, credential:
        async for rg in client.resource_groups.list():
            logging.info('...%s (%s)', rg.name, rg.id)
            rg_msgs.append(json.dumps(rg.serialize(keep_readonly=True)))

    msgs.set(rg_msgs)

    logging.info('Done.')
