import os
from datetime import datetime
from typing import Any

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

load_dotenv()

app = FastAPI()

RECIPE_FIELDS: list[str] = ["title", "making_time", "serves", "ingredients", "cost"]
LIST_COLUMNS: str = "id, title, making_time, serves, ingredients, cost"
FULL_COLUMNS: str = "id, title, making_time, serves, ingredients, cost, created_at, updated_at"

# Messages: check each one against the problem statement before submitting.
MSG_CREATE_SUCCESS: str = "Recipe successfully created!"
MSG_CREATE_FAILED: str = "Recipe creation failed!"
MSG_DETAILS: str = "Recipe details by id"
MSG_UPDATE_SUCCESS: str = "Recipe successfully updated!"
MSG_DELETE_SUCCESS: str = "Recipe successfully removed!"
MSG_NOT_FOUND: str = "No recipe found"


class RecipeInput(BaseModel):
    # All fields are optional so that FastAPI never returns 422 by itself.
    title: str | None = None
    making_time: str | None = None
    serves: str | None = None
    ingredients: str | None = None
    cost: int | str | None = None


def get_connection() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        ssl={"ssl": {}},
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4",
        autocommit=True,
    )


def format_row(row: dict[str, Any]) -> dict[str, Any]:
    # Convert datetime values to "YYYY-MM-DD HH:MM:SS".
    formatted: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            formatted[key] = value.strftime("%Y-%m-%d %H:%M:%S")
        else:
            formatted[key] = value
    return formatted


def find_recipe(cur: pymysql.cursors.DictCursor, recipe_id: int, columns: str) -> dict[str, Any] | None:
    cur.execute(f"SELECT {columns} FROM recipes WHERE id = %s", (recipe_id,))
    return cur.fetchone()


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Undefined paths (404) and undefined methods (405) both return 404.
    if exc.status_code in (404, 405):
        return JSONResponse(status_code=404, content={"message": "Not Found"})
    return JSONResponse(status_code=exc.status_code, content={"message": str(exc.detail)})


@app.post("/recipes")
def create_recipe(recipe: RecipeInput) -> dict[str, Any]:
    values: dict[str, Any] = recipe.model_dump()
    if any(values[field] is None or values[field] == "" for field in RECIPE_FIELDS):
        return {
            "message": MSG_CREATE_FAILED,
            "required": "title, making_time, serves, ingredients, cost",
        }

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO recipes (title, making_time, serves, ingredients, cost) "
                "VALUES (%s, %s, %s, %s, %s)",
                tuple(values[field] for field in RECIPE_FIELDS),
            )
            new_id: int = cur.lastrowid
            row = find_recipe(cur, new_id, FULL_COLUMNS)

    return {"message": MSG_CREATE_SUCCESS, "recipe": [format_row(row)]}


@app.get("/recipes")
def get_recipes() -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {LIST_COLUMNS} FROM recipes")
            rows: list[dict[str, Any]] = cur.fetchall()
    return {"recipes": [format_row(row) for row in rows]}


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            row = find_recipe(cur, recipe_id, LIST_COLUMNS)
    if row is None:
        return {"message": MSG_NOT_FOUND}
    return {"message": MSG_DETAILS, "recipe": [format_row(row)]}


@app.patch("/recipes/{recipe_id}")
def update_recipe(recipe_id: int, recipe: RecipeInput) -> dict[str, Any]:
    # Only the fields that were actually sent are updated.
    updates: dict[str, Any] = recipe.model_dump(exclude_none=True)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check existence first: MySQL reports 0 affected rows when values are unchanged.
            if find_recipe(cur, recipe_id, "id") is None:
                return {"message": MSG_NOT_FOUND}

            if updates:
                set_clause: str = ", ".join(f"{field} = %s" for field in updates)
                cur.execute(
                    f"UPDATE recipes SET {set_clause} WHERE id = %s",
                    (*updates.values(), recipe_id),
                )

            row = find_recipe(cur, recipe_id, "title, making_time, serves, ingredients, cost")

    return {"message": MSG_UPDATE_SUCCESS, "recipe": [format_row(row)]}


@app.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
            deleted: bool = cur.rowcount > 0
    if not deleted:
        return {"message": MSG_NOT_FOUND}
    return {"message": MSG_DELETE_SUCCESS}