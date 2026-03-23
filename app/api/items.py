import uuid

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.models.item import Item, ItemCreate

router = APIRouter(prefix="/items", tags=["items"])

# Initialize DynamoDB inside module scope but wait to fetch the table name from settings
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")


def get_table():
    return dynamodb.Table(settings.dynamodb_table_name)


@router.post("/", response_model=Item)
def create_item(item: ItemCreate):
    table = get_table()
    item_id = str(uuid.uuid4())
    new_item = Item(id=item_id, **item.model_dump())

    try:
        table.put_item(Item=new_item.model_dump())
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return new_item


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: str):
    table = get_table()
    try:
        response = table.get_item(Key={"id": item_id})
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "Item" not in response:
        raise HTTPException(status_code=404, detail="Item not found")

    return response["Item"]
