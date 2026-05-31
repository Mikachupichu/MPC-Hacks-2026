from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_collection

router = APIRouter()


@router.get("/transactions")
async def list_transactions(
    department: str | None = None,
    category: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
):
    """List transactions with optional filtering."""
    try:
        collection = await get_collection("transactions")
        query = {}

        if department:
            query["department"] = department
        if category:
            query["category"] = category
        if status:
            query["approval_status"] = status

        total = await collection.count_documents(query)
        cursor = collection.find(query, {"_id": 0}).sort("date", -1).skip(offset).limit(limit)
        transactions = await cursor.to_list(length=limit)

        return {
            "transactions": transactions,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/departments")
async def list_departments():
    """List all departments with aggregated stats."""
    try:
        collection = await get_collection("transactions")
        pipeline = [
            {
                "$group": {
                    "_id": "$department",
                    "count": {"$sum": 1},
                    "total": {"$sum": "$amount"},
                    "avg": {"$avg": "$amount"},
                }
            },
            {"$sort": {"total": -1}},
        ]
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=50)
        return {
            "departments": [
                {
                    "name": r["_id"],
                    "count": r["count"],
                    "total": round(r["total"], 2),
                    "avg": round(r["avg"], 2),
                }
                for r in results
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/categories")
async def list_categories():
    """List all categories with aggregated stats."""
    try:
        collection = await get_collection("transactions")
        pipeline = [
            {
                "$group": {
                    "_id": "$category",
                    "count": {"$sum": 1},
                    "total": {"$sum": "$amount"},
                    "avg": {"$avg": "$amount"},
                }
            },
            {"$sort": {"total": -1}},
        ]
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=50)
        return {
            "categories": [
                {
                    "name": r["_id"],
                    "count": r["count"],
                    "total": round(r["total"], 2),
                    "avg": round(r["avg"], 2),
                }
                for r in results
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
