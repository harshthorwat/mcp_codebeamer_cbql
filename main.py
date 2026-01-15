import logging
from typing import Optional

from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_http_headers

from utils.codebeamer_client import CodebeamerClient
from utils.errors import RateLimited

class CodebeamerCBQL:
    def __init__(self) -> None:
        self.client = CodebeamerClient()
        self.mcp = FastMCP("Codebeamer MCP")
        self._register_tools()

    def _register_tools(self):
        
        @self.mcp.tool(
            name="List projects",
            description="List all Codebeamer projects accessible to the current user."
        )
        async def list_projects():
            
            # Get access token from the tool call request
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            try:
                projects = await self.client.request(token=access_token, method="GET", path="v3/projects")
                return {
                    "projects": [
                        {
                            "id": p["id"], "name": p["name"]
                        }
                        for p in projects
                    ]
                }
            
            except RateLimited as e:
                raise RuntimeError(f"RATE_LIMITED: {e.retry_after}")
            
        @self.mcp.tool(
            name="List trackers",
            description="List all trackers within a given Codebeamer project."
        )
        async def list_trackers(project_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            trackers = await self.client.request(
                token=access_token,
                method="GET",
                path=f"/v3/projects/{project_id}/trackers"
            )

            return {
                "trackers": [
                    {
                        "id": t["id"],
                        "name": t["name"],
                        "type": t.get("type")
                    }
                    for t in trackers
                ]
            }
        
        @self.mcp.tool(
                name="query_items",
                description="Always write one CBQL expression that returns all required items."
        )
        async def query_items(
            ctx: Context,
            cbql: str, 
            page_size: Optional[int] = 500
        ):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            page = 1
            all_items = []

            await ctx.stream({
                "event": "START",
                "message": "Executing CBQL query"
            })

            try:
                while True:
                    result = await self.client.request(
                        token=access_token,
                        method="POST", 
                        path="/v3/items/query",
                        json={
                            "queryString": cbql,
                            "page": page, 
                            "pageSize": page_size
                        }
                    )

                    items = result.get("items", [])
                    all_items.extend(items)
                    
                    await ctx.stream({
                        "event": "PROGRESS",
                        "page": page,
                        "itemsFetched": len(items)
                    })

                    if len(items) < page_size:
                        break
                    
                    page += 1

                return {
                    "totalCount": len(all_items),
                    "items": all_items
                }
            
            except RateLimited as e:
                raise RuntimeError(f"RATE_LIMITED: {e.retry_after}")

        @self.mcp.tool(
            name="extend_relations",
            description="Fetch upstream and downstream relations for multiple items in bulk."
        )
        async def expand_relations(item_ids: list[int]):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            relations = await self.client.request(
                token=access_token,
                method="POST", 
                path="v3/items/relations",
                json={
                    "items": item_ids
                }
            )

            return {
                "relations": relations
            }
        
        @self.mcp.tool(
                name="bulk_update_items", 
                description="Update fields for multiple Codebeamer items in a single request."
        )
        async def bulk_update_items(
            updates: list[dict],
            atomic: bool = True
        ):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            result = await self.client.request(
                token=access_token,
                method="PUT", 
                path="/v3/items/fields",
                params={
                    "atomic": atomic
                },
                json=updates
            )

            return {
                "result": result
            }
        
        @self.mcp.tool(
                name="item_action",
                description="Perform a single explicit action on a Codebeamer item."
        )
        async def item_action(
            item_id: int, 
            action: str, 
            payload: dict
        ):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            if action == "comment":
                result = await self.client.request(
                    token=access_token,
                    method="POST",
                    path=f"/v3/items/{item_id}/comments",
                    files=payload
                )
            elif action == "transition":
                result = await self.client.request(
                    token=access_token,
                    method="PUT",
                    path=f"/v3/items/{item_id}",
                    json=payload
                )
            else:
                raise ValueError("Unsupported action")
            
            return {
                "result": result
            }
        
        @self.mcp.tool(
                name="export_items", 
                description="Export a list of Codebeamer items efficiently."
        )
        async def export_items(item_ids: list[int]):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            job = await self.client.request(
                token=access_token,
                method="POST",
                path="/v3/export/items",
                json={
                    "items": item_ids
                }
            )

            return {
                "job": job
            }
        
        @self.mcp.tool(
            name="get_project_details",
            description="Get detailed metadata for a specific Codebeamer project."
        )
        async def get_project_details(project_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            try:
                project = await self.client.request(
                    token=access_token,
                    method="GET", 
                    path=f"/v3/projects/{project_id}"
                )

                return {
                    "id": project["id"],
                    "name": project["name"],
                    "description": project.get("description"),
                    "key": project.get("key"),
                    "createdAt": project.get("createdAt"),
                    "status": project.get("status")
                }

            except RateLimited as e:
                raise RuntimeError(f"RATE_LIMITED:{e.retry_after}")

        @self.mcp.tool(
            name="get_tracker_details",
            description="Get detailed metadata for a specific tracker."
        )
        async def get_tracker_details(tracker_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            tracker = await self.client.request(
                token=access_token,
                method="GET", 
                path=f"/v3/trackers/{tracker_id}"
            )

            return {
                "id": tracker["id"],
                "name": tracker["name"],
                "type": tracker["type"],
                "description": tracker.get("description"),
                "projectId": tracker["project"]["id"]
            }

        @self.mcp.tool(
            name="get_item_details",
            description="Get full details of a single tracker item."
        )
        async def get_item_details(item_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            item = await self.client.request(
                token=access_token,
                method="GET", 
                path=f"/v3/items/{item_id}"
            )

            return item

        @self.mcp.tool(
            name="get_item_history",
            description="Get change history for a tracker item."
        )
        async def get_item_history(item_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            history = await self.client.request(
                token=access_token,
                method="GET", 
                path=f"/v3/items/{item_id}/history"
            )

            return {"history": history}

        @self.mcp.tool(
            name="get_item_fields",
            description="Get all fields and values of a tracker item."
        )
        async def get_item_fields(item_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            fields = await self.client.request(
                token=access_token,
                method="GET", 
                path=f"/v3/items/{item_id}/fields"
            )

            return {"fields": fields}

        @self.mcp.tool(
            name="create_item",
            description="Create a new tracker item."
        )
        async def create_item(tracker_id: int, fields: dict):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            item = await self.client.request(
                token=access_token,
                method="POST",
                path="/v3/items",
                json={
                    "tracker": {"id": tracker_id},
                    "fields": fields
                }
            )

            return {"item": item}
        
        @self.mcp.tool(
            name="delete_item",
            description="Delete (trash) a tracker item."
        )
        async def delete_item(item_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            await self.client.request(
                token=access_token,
                method="DELETE", 
                path=f"/v3/items/{item_id}"
            )

            return {"deleted": True, "itemId": item_id}

        @self.mcp.tool(
            name="get_item_transitions",
            description="Get allowed workflow transitions for an item."
        )
        async def get_item_transitions(item_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            transitions = await self.client.request(
                token=access_token,
                method="GET", 
                path=f"/v3/items/{item_id}/transitions"
            )

            return {"transitions": transitions}

        @self.mcp.tool(
            name="create_association",
            description="Create a relation between two items."
        )
        async def create_association(
            source_item_id: int,
            target_item_id: int,
            association_type_id: int
        ):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            association = await self.client.request(
                token=access_token,
                method="POST",
                path="/v3/associations",
                json={
                    "sourceItem": {"id": source_item_id},
                    "targetItem": {"id": target_item_id},
                    "type": {"id": association_type_id}
                }
            )

            return {"association": association}


        @self.mcp.tool(
            name="delete_association",
            description="Delete an association between items."
        )
        async def delete_association(association_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            await self.client.request(
                token=access_token,
                method="DELETE", 
                path=f"/v3/associations/{association_id}"
            )

            return {"deleted": True, "associationId": association_id}

        @self.mcp.tool(
            name="list_association_types",
            description="List all available association types."
        )
        async def list_association_types():
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            types = await self.client.request(
                token=access_token,
                method="GET", 
                path="/v3/associations/types"
            )

            return {"associationTypes": types}


        @self.mcp.tool(
            name="get_item_children",
            description="Get child items of a tracker item."
        )
        async def get_item_children(item_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            children = await self.client.request(
                token=access_token,
                method="GET", 
                path=f"/v3/items/{item_id}/children"
            )

            return {"children": children}

        @self.mcp.tool(
            name="add_item_child",
            description="Add a child item under a parent."
        )
        async def add_item_child(parent_id: int, child_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            result = await self.client.request(
                token=access_token,
                method="POST",
                path=f"/v3/items/{parent_id}/children",
                json={"items": [{"id": child_id}]}
            )

            return {"result": result}

        @self.mcp.tool(
            name="list_comments",
            description="List comments on an item."
        )
        async def list_comments(item_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            comments = await self.client.request(
                token=access_token,
                method="GET", 
                path=f"/v3/items/{item_id}/comments"
            )

            return {"comments": comments}
        
        @self.mcp.tool(
            name="update_comment",
            description="Update a comment on an item."
        )
        async def update_comment(item_id: int, comment_id: int, text: str):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            comment = await self.client.request(
                token=access_token,
                method="PUT",
                path=f"/v3/items/{item_id}/comments/{comment_id}",
                json={"text": text}
            )

            return {"comment": comment}

        @self.mcp.tool(
            name="delete_comment",
            description="Delete a comment from an item."
        )
        async def delete_comment(item_id: int, comment_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            await self.client.request(
                token=access_token,
                method="DELETE",
                path=f"/v3/items/{item_id}/comments/{comment_id}"
            )

            return {"deleted": True}

        @self.mcp.tool(
            name="list_attachments",
            description="List attachments of an item."
        )
        async def list_attachments(item_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            attachments = await self.client.request(
                token=access_token,
                method="GET", 
                path=f"/v3/items/{item_id}/attachments"
            )

            return {"attachments": attachments}

        @self.mcp.tool(
            name="delete_attachment",
            description="Delete an attachment from an item."
        )
        async def delete_attachment(item_id: int, attachment_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            await self.client.request(
                token=access_token,
                method="DELETE",
                path=f"/v3/items/{item_id}/attachments/{attachment_id}"
            )

            return {"deleted": True}
        
        @self.mcp.tool(
            name="lock_item",
            description="Lock a tracker item."
        )
        async def lock_item(item_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            await self.client.request(
                token=access_token,
                method="PUT", 
                path=f"/v3/items/{item_id}/lock"
            )

            return {"locked": True}

        @self.mcp.tool(
            name="unlock_item",
            description="Unlock a tracker item."
        )
        async def unlock_item(item_id: int):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            await self.client.request(
                token=access_token,
                method="DELETE", 
                path=f"/v3/items/{item_id}/lock"
            )

            return {"locked": False}

        @self.mcp.tool(
            name="create_baseline",
            description="Create a baseline snapshot."
        )
        async def create_baseline(project_id: int, name: str):
            received_headers = get_http_headers()
            access_token = received_headers.get("authorization") or received_headers.get("Authorization") or received_headers.get("x-access-token")

            baseline = await self.client.request(
                token=access_token,
                method="POST",
                path="/v3/baselines",
                json={
                    "project": {"id": project_id},
                    "name": name
                }
            )

            return {"baseline": baseline}


        def start(self):
            try:
                self.mcp.run(
                    transport="streamable-http",
                    host="0.0.0.0",
                    port=8000,
                )
            except Exception as e:
                logging.exception(
                    f"Failed to start Codebeamer CBQL MCP server with error: {e}"
                )
        

if __name__ == "__main__":
    server = CodebeamerCBQL()
    server.start()