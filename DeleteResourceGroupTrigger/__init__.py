import logging

import azure.functions as func

from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.core.tools import parse_resource_id
from azure.mgmt.resource.resources.aio import ResourceManagementClient
from azure.mgmt.resource.locks.aio import ManagementLockClient
from azure.mgmt.resource.resources.models import ResourceGroup


async def main(msg: func.QueueMessage) -> None:

    rg = ResourceGroup.deserialize(msg.get_json())

    rg_id = parse_resource_id(rg.id)
    sub_id = rg_id['subscription']

    logging.info('Starting delete task for Resource Group: %s', rg.name)

    credential = DefaultAzureCredential()

    logging.info('Getting Management Locks for Resource Group...')

    async with credential, ManagementLockClient(credential=credential, subscription_id=sub_id) as client:
        async for lock in client.management_locks.list_at_resource_group_level(rg.name):
            logging.info('Deleting Management Lock: %s', lock.name)
            await client.management_locks.delete_at_resource_group_level(rg.name, lock.name)

    logging.info('Deleting Resource Group...')

    async with credential, ResourceManagementClient(credential=credential, subscription_id=sub_id) as client:
        rg_delete = await client.resource_groups.begin_delete(rg.name)
        await rg_delete.result()

    logging.info('Done.')
