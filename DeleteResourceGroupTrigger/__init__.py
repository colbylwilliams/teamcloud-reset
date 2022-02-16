import logging

import azure.functions as func

from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.core.tools import parse_resource_id
from azure.mgmt.resource.resources.aio import ResourceManagementClient
from azure.mgmt.resource.locks.aio import ManagementLockClient
from azure.mgmt.resource.resources.models import ResourceGroup


async def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))

    rg = ResourceGroup.deserialize(msg.get_json())

    rg_id = parse_resource_id(rg.id)
    sub_id = rg_id['subscription']

    logging.info('Starting Delete task for Resource Group %s (%s)', rg.name, rg.id)

    credential = DefaultAzureCredential(logging_enable=True)
    lock_client = ManagementLockClient(credential=credential, subscription_id=sub_id)
    
    logging.info('Getting Management Locks for Resource Group...')

    async with lock_client, credential:
        async for lock in lock_client.management_locks.list_at_resource_group_level(rg.name):
            logging.info('Deleting Management Lock: %s', lock.name)
            await lock_client.management_locks.delete_at_resource_group_level(rg.name, lock.name)

    logging.info('Deleting Resource Group...')

    rg_client = ResourceManagementClient(credential=credential, subscription_id=sub_id)

    async with rg_client, credential:
        rg_delete = await rg_client.resource_groups.begin_delete(rg.name)
        await rg_delete.result()

    logging.info('Done.')
