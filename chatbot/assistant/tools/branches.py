import math
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from datatable.models import BankBranch


class BranchLocatorSchema(BaseModel):
    latitude: float | None = Field(None, description="The latitude coordinate")
    longitude: float | None = Field(None, description="The longitude coordinate")
    only_closest: bool = Field(
        default=False, description="Whether to return only the closest branch"
    )
    limit: int = Field(
        default=3, description="Maximum number of branches to return (for pagination)"
    )
    skip: int = Field(
        default=0, description="Number of branches to skip (for pagination)"
    )


class BranchLocatorTool(BaseTool):
    name: str = "branch_locator"
    description: str = "Find branches with pagination support. Use limit and skip for pagination (e.g., skip=0,limit=3 for first page, skip=3,limit=3 for second page, etc.)"
    args_schema: Type[BaseModel] = BranchLocatorSchema

    def _run(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        only_closest: bool = False,
        limit: int = 3,
        skip: int = 0,
    ) -> dict:
        if only_closest and latitude and longitude:
            closest = BankBranch.find_closest(latitude, longitude)
            branches = [
                {
                    "id": branch["id"],
                    "name": branch["name"],
                    "address": branch["address"],
                    "distance": branch["distance"],
                    "map_url": f"https://www.google.com/maps/dir/?api=1&destination={branch.get('langtitude_cordinates', '')},{branch.get('longitude_cordinates', '')}"
                    if branch.get("langtitude_cordinates")
                    and branch.get("longitude_cordinates")
                    else None,
                }
                for branch in closest
            ]
            return {
                "branches": branches,
                "pagination": {
                    "total": len(branches),
                    "skip": skip,
                    "limit": limit,
                    "has_more": False,
                },
            }
        else:
            all_branches = BankBranch.objects.all()
            total_count = all_branches.count()

            paginated_branches = all_branches[skip : skip + limit]

            branches = []
            for branch in paginated_branches:
                branch_data = {
                    "id": getattr(branch, "id", None),
                    "name": getattr(branch, "name", ""),
                    "address": getattr(branch, "address", ""),
                }

                lat_coord = getattr(branch, "langtitude_cordinates", None)
                lon_coord = getattr(branch, "longitude_cordinates", None)

                if lat_coord and lon_coord:
                    branch_data["map_url"] = (
                        f"https://www.google.com/maps/dir/?api=1&destination={lat_coord},{lon_coord}"
                    )

                    if latitude and longitude:
                        try:
                            distance = self.haversine_distance(
                                latitude, longitude, lat_coord, lon_coord
                            )
                            branch_data["distance"] = round(distance, 2)
                        except (ValueError, TypeError):
                            pass

                branches.append(branch_data)

            return {
                "branches": branches,
                "pagination": {
                    "total": total_count,
                    "skip": skip,
                    "limit": limit,
                    "has_more": skip + limit < total_count,
                    "next_skip": skip + limit if skip + limit < total_count else None,
                    "current_page": (skip // limit) + 1,
                    "total_pages": (total_count + limit - 1) // limit,
                },
            }

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance
