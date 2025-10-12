# GridBoss API Specification

_Generated via `python scripts/generate_api_docs.py`_

```json
{
  "components": {
    "schemas": {
      "AdminLeagueSummary": {
        "properties": {
          "billing_plan": {
            "title": "Billing Plan",
            "type": "string"
          },
          "discord_active": {
            "title": "Discord Active",
            "type": "boolean"
          },
          "driver_count": {
            "title": "Driver Count",
            "type": "integer"
          },
          "driver_limit": {
            "title": "Driver Limit",
            "type": "integer"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "name": {
            "title": "Name",
            "type": "string"
          },
          "owner_discord_username": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Owner Discord Username"
          },
          "owner_email": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Owner Email"
          },
          "owner_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Owner Id"
          },
          "plan": {
            "title": "Plan",
            "type": "string"
          },
          "slug": {
            "title": "Slug",
            "type": "string"
          }
        },
        "required": [
          "id",
          "name",
          "slug",
          "plan",
          "driver_limit",
          "driver_count",
          "owner_id",
          "owner_discord_username",
          "owner_email",
          "billing_plan",
          "discord_active"
        ],
        "title": "AdminLeagueSummary",
        "type": "object"
      },
      "AdminSearchResponse": {
        "properties": {
          "leagues": {
            "items": {
              "$ref": "#/components/schemas/AdminLeagueSummary"
            },
            "title": "Leagues",
            "type": "array"
          },
          "users": {
            "items": {
              "$ref": "#/components/schemas/AdminUserSummary"
            },
            "title": "Users",
            "type": "array"
          }
        },
        "required": [
          "users",
          "leagues"
        ],
        "title": "AdminSearchResponse",
        "type": "object"
      },
      "AdminUserSummary": {
        "properties": {
          "billing_plan": {
            "title": "Billing Plan",
            "type": "string"
          },
          "created_at": {
            "format": "date-time",
            "title": "Created At",
            "type": "string"
          },
          "discord_username": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Discord Username"
          },
          "email": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Email"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "leagues_owned": {
            "title": "Leagues Owned",
            "type": "integer"
          },
          "stripe_customer_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Stripe Customer Id"
          },
          "subscription_status": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Subscription Status"
          }
        },
        "required": [
          "id",
          "discord_username",
          "email",
          "created_at",
          "leagues_owned",
          "billing_plan",
          "subscription_status",
          "stripe_customer_id"
        ],
        "title": "AdminUserSummary",
        "type": "object"
      },
      "AuditLogPage": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/AuditLogRead"
            },
            "title": "Items",
            "type": "array"
          },
          "page": {
            "title": "Page",
            "type": "integer"
          },
          "page_size": {
            "title": "Page Size",
            "type": "integer"
          },
          "total": {
            "title": "Total",
            "type": "integer"
          }
        },
        "required": [
          "items",
          "page",
          "page_size",
          "total"
        ],
        "title": "AuditLogPage",
        "type": "object"
      },
      "AuditLogRead": {
        "properties": {
          "action": {
            "title": "Action",
            "type": "string"
          },
          "actor_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Actor Id"
          },
          "after_state": {
            "anyOf": [
              {},
              {
                "type": "null"
              }
            ],
            "title": "After State"
          },
          "before_state": {
            "anyOf": [
              {},
              {
                "type": "null"
              }
            ],
            "title": "Before State"
          },
          "entity": {
            "title": "Entity",
            "type": "string"
          },
          "entity_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Entity Id"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "league_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "League Id"
          },
          "timestamp": {
            "format": "date-time",
            "title": "Timestamp",
            "type": "string"
          }
        },
        "required": [
          "id",
          "timestamp",
          "actor_id",
          "league_id",
          "entity",
          "entity_id",
          "action",
          "before_state",
          "after_state"
        ],
        "title": "AuditLogRead",
        "type": "object"
      },
      "BillingLeagueUsage": {
        "properties": {
          "driver_count": {
            "title": "Driver Count",
            "type": "integer"
          },
          "driver_limit": {
            "title": "Driver Limit",
            "type": "integer"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "name": {
            "title": "Name",
            "type": "string"
          },
          "plan": {
            "title": "Plan",
            "type": "string"
          },
          "slug": {
            "title": "Slug",
            "type": "string"
          }
        },
        "required": [
          "id",
          "name",
          "slug",
          "plan",
          "driver_limit",
          "driver_count"
        ],
        "title": "BillingLeagueUsage",
        "type": "object"
      },
      "BillingOverviewResponse": {
        "properties": {
          "can_manage_subscription": {
            "title": "Can Manage Subscription",
            "type": "boolean"
          },
          "current_period_end": {
            "anyOf": [
              {
                "format": "date-time",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Current Period End"
          },
          "grace_expires_at": {
            "anyOf": [
              {
                "format": "date-time",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Grace Expires At"
          },
          "grace_plan": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Grace Plan"
          },
          "leagues": {
            "items": {
              "$ref": "#/components/schemas/BillingLeagueUsage"
            },
            "title": "Leagues",
            "type": "array"
          },
          "plan": {
            "title": "Plan",
            "type": "string"
          }
        },
        "required": [
          "plan",
          "current_period_end",
          "grace_plan",
          "grace_expires_at",
          "can_manage_subscription",
          "leagues"
        ],
        "title": "BillingOverviewResponse",
        "type": "object"
      },
      "BillingPlanOut": {
        "properties": {
          "current_period_end": {
            "anyOf": [
              {
                "format": "date-time",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Current Period End"
          },
          "plan": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Plan"
          }
        },
        "required": [
          "plan",
          "current_period_end"
        ],
        "title": "BillingPlanOut",
        "type": "object"
      },
      "CheckoutRequest": {
        "properties": {
          "plan": {
            "enum": [
              "PRO",
              "ELITE"
            ],
            "title": "Plan",
            "type": "string"
          }
        },
        "required": [
          "plan"
        ],
        "title": "CheckoutRequest",
        "type": "object"
      },
      "CheckoutResponse": {
        "properties": {
          "url": {
            "format": "uri",
            "minLength": 1,
            "title": "Url",
            "type": "string"
          }
        },
        "required": [
          "url"
        ],
        "title": "CheckoutResponse",
        "type": "object"
      },
      "DiscordIntegrationRead": {
        "properties": {
          "channel_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Channel Id"
          },
          "guild_id": {
            "title": "Guild Id",
            "type": "string"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "installed_by_user": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Installed By User"
          },
          "is_active": {
            "title": "Is Active",
            "type": "boolean"
          },
          "league_id": {
            "format": "uuid",
            "title": "League Id",
            "type": "string"
          }
        },
        "required": [
          "id",
          "league_id",
          "guild_id",
          "channel_id",
          "installed_by_user",
          "is_active"
        ],
        "title": "DiscordIntegrationRead",
        "type": "object"
      },
      "DiscordLinkRequest": {
        "properties": {
          "channel_id": {
            "minLength": 1,
            "title": "Channel Id",
            "type": "string"
          },
          "guild_id": {
            "minLength": 1,
            "title": "Guild Id",
            "type": "string"
          }
        },
        "required": [
          "guild_id",
          "channel_id"
        ],
        "title": "DiscordLinkRequest",
        "type": "object"
      },
      "DiscordToggleRequest": {
        "properties": {
          "is_active": {
            "title": "Is Active",
            "type": "boolean"
          }
        },
        "required": [
          "is_active"
        ],
        "title": "DiscordToggleRequest",
        "type": "object"
      },
      "DriverBulkCreate": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/DriverCreateItem"
            },
            "minItems": 1,
            "title": "Items",
            "type": "array"
          }
        },
        "required": [
          "items"
        ],
        "title": "DriverBulkCreate",
        "type": "object"
      },
      "DriverCreateItem": {
        "properties": {
          "display_name": {
            "minLength": 1,
            "title": "Display Name",
            "type": "string"
          },
          "team_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Team Id"
          }
        },
        "required": [
          "display_name"
        ],
        "title": "DriverCreateItem",
        "type": "object"
      },
      "DriverRead": {
        "properties": {
          "discord_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Discord Id"
          },
          "display_name": {
            "title": "Display Name",
            "type": "string"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "league_id": {
            "format": "uuid",
            "title": "League Id",
            "type": "string"
          },
          "team_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Team Id"
          },
          "team_name": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Team Name"
          },
          "user_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "User Id"
          }
        },
        "required": [
          "id",
          "league_id",
          "display_name",
          "user_id",
          "discord_id",
          "team_id",
          "team_name"
        ],
        "title": "DriverRead",
        "type": "object"
      },
      "DriverUpdate": {
        "properties": {
          "display_name": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Display Name"
          },
          "team_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Team Id"
          }
        },
        "title": "DriverUpdate",
        "type": "object"
      },
      "EventCreate": {
        "properties": {
          "distance_km": {
            "anyOf": [
              {
                "exclusiveMinimum": 0.0,
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Distance Km"
          },
          "laps": {
            "anyOf": [
              {
                "exclusiveMinimum": 0.0,
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Laps"
          },
          "name": {
            "minLength": 1,
            "title": "Name",
            "type": "string"
          },
          "season_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Season Id"
          },
          "start_time": {
            "format": "date-time",
            "title": "Start Time",
            "type": "string"
          },
          "track": {
            "minLength": 1,
            "title": "Track",
            "type": "string"
          }
        },
        "required": [
          "name",
          "track",
          "start_time"
        ],
        "title": "EventCreate",
        "type": "object"
      },
      "EventRead": {
        "properties": {
          "distance_km": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Distance Km"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "laps": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Laps"
          },
          "league_id": {
            "format": "uuid",
            "title": "League Id",
            "type": "string"
          },
          "name": {
            "title": "Name",
            "type": "string"
          },
          "season_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Season Id"
          },
          "start_time": {
            "format": "date-time",
            "title": "Start Time",
            "type": "string"
          },
          "status": {
            "$ref": "#/components/schemas/EventStatus"
          },
          "track": {
            "title": "Track",
            "type": "string"
          }
        },
        "required": [
          "id",
          "league_id",
          "season_id",
          "name",
          "track",
          "start_time",
          "laps",
          "distance_km",
          "status"
        ],
        "title": "EventRead",
        "type": "object"
      },
      "EventResultsRead": {
        "properties": {
          "event_id": {
            "format": "uuid",
            "title": "Event Id",
            "type": "string"
          },
          "items": {
            "items": {
              "$ref": "#/components/schemas/ResultEntryRead"
            },
            "title": "Items",
            "type": "array"
          },
          "league_id": {
            "format": "uuid",
            "title": "League Id",
            "type": "string"
          },
          "season_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Season Id"
          }
        },
        "required": [
          "event_id",
          "league_id",
          "season_id",
          "items"
        ],
        "title": "EventResultsRead",
        "type": "object"
      },
      "EventStatus": {
        "enum": [
          "SCHEDULED",
          "COMPLETED",
          "CANCELED"
        ],
        "title": "EventStatus",
        "type": "string"
      },
      "EventUpdate": {
        "properties": {
          "distance_km": {
            "anyOf": [
              {
                "exclusiveMinimum": 0.0,
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Distance Km"
          },
          "laps": {
            "anyOf": [
              {
                "exclusiveMinimum": 0.0,
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Laps"
          },
          "name": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Name"
          },
          "season_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Season Id"
          },
          "start_time": {
            "anyOf": [
              {
                "format": "date-time",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Start Time"
          },
          "status": {
            "anyOf": [
              {
                "$ref": "#/components/schemas/EventStatus"
              },
              {
                "type": "null"
              }
            ]
          },
          "track": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Track"
          }
        },
        "title": "EventUpdate",
        "type": "object"
      },
      "HTTPValidationError": {
        "properties": {
          "detail": {
            "items": {
              "$ref": "#/components/schemas/ValidationError"
            },
            "title": "Detail",
            "type": "array"
          }
        },
        "title": "HTTPValidationError",
        "type": "object"
      },
      "LeagueCreate": {
        "properties": {
          "name": {
            "title": "Name",
            "type": "string"
          },
          "slug": {
            "title": "Slug",
            "type": "string"
          }
        },
        "required": [
          "name",
          "slug"
        ],
        "title": "LeagueCreate",
        "type": "object"
      },
      "LeagueRead": {
        "properties": {
          "deleted_at": {
            "anyOf": [
              {
                "format": "date-time",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Deleted At"
          },
          "driver_limit": {
            "title": "Driver Limit",
            "type": "integer"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "is_deleted": {
            "title": "Is Deleted",
            "type": "boolean"
          },
          "name": {
            "title": "Name",
            "type": "string"
          },
          "owner_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Owner Id"
          },
          "plan": {
            "title": "Plan",
            "type": "string"
          },
          "slug": {
            "title": "Slug",
            "type": "string"
          }
        },
        "required": [
          "id",
          "name",
          "slug",
          "plan",
          "driver_limit",
          "owner_id",
          "is_deleted",
          "deleted_at"
        ],
        "title": "LeagueRead",
        "type": "object"
      },
      "LeagueRole": {
        "enum": [
          "OWNER",
          "ADMIN",
          "STEWARD",
          "DRIVER"
        ],
        "title": "LeagueRole",
        "type": "string"
      },
      "LeagueUpdate": {
        "properties": {
          "name": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Name"
          },
          "slug": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Slug"
          }
        },
        "title": "LeagueUpdate",
        "type": "object"
      },
      "MeResponse": {
        "properties": {
          "billingPlan": {
            "anyOf": [
              {
                "$ref": "#/components/schemas/BillingPlanOut"
              },
              {
                "type": "null"
              }
            ]
          },
          "memberships": {
            "items": {
              "$ref": "#/components/schemas/MembershipOut"
            },
            "title": "Memberships",
            "type": "array"
          },
          "user": {
            "$ref": "#/components/schemas/UserOut"
          }
        },
        "required": [
          "user",
          "memberships",
          "billingPlan"
        ],
        "title": "MeResponse",
        "type": "object"
      },
      "MembershipCreate": {
        "properties": {
          "role": {
            "$ref": "#/components/schemas/LeagueRole"
          },
          "user_id": {
            "format": "uuid",
            "title": "User Id",
            "type": "string"
          }
        },
        "required": [
          "user_id",
          "role"
        ],
        "title": "MembershipCreate",
        "type": "object"
      },
      "MembershipOut": {
        "properties": {
          "league_id": {
            "format": "uuid",
            "title": "League Id",
            "type": "string"
          },
          "league_name": {
            "title": "League Name",
            "type": "string"
          },
          "league_slug": {
            "title": "League Slug",
            "type": "string"
          },
          "role": {
            "$ref": "#/components/schemas/LeagueRole"
          }
        },
        "required": [
          "league_id",
          "league_slug",
          "league_name",
          "role"
        ],
        "title": "MembershipOut",
        "type": "object"
      },
      "MembershipRead": {
        "properties": {
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "league_id": {
            "format": "uuid",
            "title": "League Id",
            "type": "string"
          },
          "role": {
            "$ref": "#/components/schemas/LeagueRole"
          },
          "user_id": {
            "format": "uuid",
            "title": "User Id",
            "type": "string"
          }
        },
        "required": [
          "id",
          "league_id",
          "user_id",
          "role"
        ],
        "title": "MembershipRead",
        "type": "object"
      },
      "MembershipUpdate": {
        "properties": {
          "role": {
            "$ref": "#/components/schemas/LeagueRole"
          }
        },
        "required": [
          "role"
        ],
        "title": "MembershipUpdate",
        "type": "object"
      },
      "PlanOverrideRequest": {
        "properties": {
          "plan": {
            "title": "Plan",
            "type": "string"
          }
        },
        "required": [
          "plan"
        ],
        "title": "PlanOverrideRequest",
        "type": "object"
      },
      "PointsRuleInput": {
        "properties": {
          "points": {
            "minimum": 0.0,
            "title": "Points",
            "type": "integer"
          },
          "position": {
            "exclusiveMinimum": 0.0,
            "title": "Position",
            "type": "integer"
          }
        },
        "required": [
          "position",
          "points"
        ],
        "title": "PointsRuleInput",
        "type": "object"
      },
      "PointsRuleRead": {
        "properties": {
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "points": {
            "title": "Points",
            "type": "integer"
          },
          "position": {
            "title": "Position",
            "type": "integer"
          }
        },
        "required": [
          "id",
          "position",
          "points"
        ],
        "title": "PointsRuleRead",
        "type": "object"
      },
      "PointsSchemeCreate": {
        "properties": {
          "is_default": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "default": false,
            "title": "Is Default"
          },
          "name": {
            "minLength": 1,
            "title": "Name",
            "type": "string"
          },
          "rules": {
            "anyOf": [
              {
                "items": {
                  "$ref": "#/components/schemas/PointsRuleInput"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ],
            "title": "Rules"
          },
          "season_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Season Id"
          }
        },
        "required": [
          "name"
        ],
        "title": "PointsSchemeCreate",
        "type": "object"
      },
      "PointsSchemeRead": {
        "properties": {
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "is_default": {
            "title": "Is Default",
            "type": "boolean"
          },
          "league_id": {
            "format": "uuid",
            "title": "League Id",
            "type": "string"
          },
          "name": {
            "title": "Name",
            "type": "string"
          },
          "rules": {
            "items": {
              "$ref": "#/components/schemas/PointsRuleRead"
            },
            "title": "Rules",
            "type": "array"
          },
          "season_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Season Id"
          }
        },
        "required": [
          "id",
          "league_id",
          "season_id",
          "name",
          "is_default",
          "rules"
        ],
        "title": "PointsSchemeRead",
        "type": "object"
      },
      "PointsSchemeUpdate": {
        "properties": {
          "is_default": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Is Default"
          },
          "name": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Name"
          },
          "rules": {
            "anyOf": [
              {
                "items": {
                  "$ref": "#/components/schemas/PointsRuleInput"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ],
            "title": "Rules"
          },
          "season_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Season Id"
          }
        },
        "title": "PointsSchemeUpdate",
        "type": "object"
      },
      "PortalResponse": {
        "properties": {
          "url": {
            "format": "uri",
            "minLength": 1,
            "title": "Url",
            "type": "string"
          }
        },
        "required": [
          "url"
        ],
        "title": "PortalResponse",
        "type": "object"
      },
      "ResultEntryCreate": {
        "properties": {
          "bonus_points": {
            "default": 0,
            "title": "Bonus Points",
            "type": "integer"
          },
          "driver_id": {
            "format": "uuid",
            "title": "Driver Id",
            "type": "string"
          },
          "finish_position": {
            "exclusiveMinimum": 0.0,
            "title": "Finish Position",
            "type": "integer"
          },
          "penalty_points": {
            "default": 0,
            "title": "Penalty Points",
            "type": "integer"
          },
          "started_position": {
            "anyOf": [
              {
                "minimum": 1.0,
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Started Position"
          },
          "status": {
            "$ref": "#/components/schemas/ResultStatus",
            "default": "FINISHED"
          }
        },
        "required": [
          "driver_id",
          "finish_position"
        ],
        "title": "ResultEntryCreate",
        "type": "object"
      },
      "ResultEntryRead": {
        "properties": {
          "bonus_points": {
            "title": "Bonus Points",
            "type": "integer"
          },
          "driver_id": {
            "format": "uuid",
            "title": "Driver Id",
            "type": "string"
          },
          "finish_position": {
            "title": "Finish Position",
            "type": "integer"
          },
          "penalty_points": {
            "title": "Penalty Points",
            "type": "integer"
          },
          "started_position": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Started Position"
          },
          "status": {
            "$ref": "#/components/schemas/ResultStatus"
          },
          "total_points": {
            "title": "Total Points",
            "type": "integer"
          }
        },
        "required": [
          "driver_id",
          "finish_position",
          "started_position",
          "status",
          "bonus_points",
          "penalty_points",
          "total_points"
        ],
        "title": "ResultEntryRead",
        "type": "object"
      },
      "ResultStatus": {
        "enum": [
          "FINISHED",
          "DNF",
          "DNS",
          "DSQ"
        ],
        "title": "ResultStatus",
        "type": "string"
      },
      "ResultSubmission": {
        "properties": {
          "entries": {
            "items": {
              "$ref": "#/components/schemas/ResultEntryCreate"
            },
            "minItems": 1,
            "title": "Entries",
            "type": "array"
          }
        },
        "required": [
          "entries"
        ],
        "title": "ResultSubmission",
        "type": "object"
      },
      "SeasonCreate": {
        "properties": {
          "is_active": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "default": false,
            "title": "Is Active"
          },
          "name": {
            "minLength": 1,
            "title": "Name",
            "type": "string"
          }
        },
        "required": [
          "name"
        ],
        "title": "SeasonCreate",
        "type": "object"
      },
      "SeasonRead": {
        "properties": {
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "is_active": {
            "title": "Is Active",
            "type": "boolean"
          },
          "league_id": {
            "format": "uuid",
            "title": "League Id",
            "type": "string"
          },
          "name": {
            "title": "Name",
            "type": "string"
          }
        },
        "required": [
          "id",
          "league_id",
          "name",
          "is_active"
        ],
        "title": "SeasonRead",
        "type": "object"
      },
      "SeasonStandingsRead": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/StandingsItem"
            },
            "title": "Items",
            "type": "array"
          },
          "league_id": {
            "format": "uuid",
            "title": "League Id",
            "type": "string"
          },
          "season_id": {
            "anyOf": [
              {
                "format": "uuid",
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Season Id"
          }
        },
        "required": [
          "league_id",
          "season_id",
          "items"
        ],
        "title": "SeasonStandingsRead",
        "type": "object"
      },
      "SeasonUpdate": {
        "properties": {
          "is_active": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Is Active"
          },
          "name": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Name"
          }
        },
        "title": "SeasonUpdate",
        "type": "object"
      },
      "StandingsItem": {
        "properties": {
          "best_finish": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Best Finish"
          },
          "display_name": {
            "title": "Display Name",
            "type": "string"
          },
          "driver_id": {
            "format": "uuid",
            "title": "Driver Id",
            "type": "string"
          },
          "points": {
            "title": "Points",
            "type": "integer"
          },
          "wins": {
            "title": "Wins",
            "type": "integer"
          }
        },
        "required": [
          "driver_id",
          "display_name",
          "points",
          "wins",
          "best_finish"
        ],
        "title": "StandingsItem",
        "type": "object"
      },
      "TeamCreate": {
        "properties": {
          "name": {
            "minLength": 1,
            "title": "Name",
            "type": "string"
          }
        },
        "required": [
          "name"
        ],
        "title": "TeamCreate",
        "type": "object"
      },
      "TeamRead": {
        "properties": {
          "driver_count": {
            "title": "Driver Count",
            "type": "integer"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "league_id": {
            "format": "uuid",
            "title": "League Id",
            "type": "string"
          },
          "name": {
            "title": "Name",
            "type": "string"
          }
        },
        "required": [
          "id",
          "league_id",
          "name",
          "driver_count"
        ],
        "title": "TeamRead",
        "type": "object"
      },
      "TeamUpdate": {
        "properties": {
          "name": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Name"
          }
        },
        "title": "TeamUpdate",
        "type": "object"
      },
      "TokenResponse": {
        "properties": {
          "access_token": {
            "title": "Access Token",
            "type": "string"
          },
          "token_type": {
            "default": "bearer",
            "title": "Token Type",
            "type": "string"
          }
        },
        "required": [
          "access_token"
        ],
        "title": "TokenResponse",
        "type": "object"
      },
      "UserOut": {
        "properties": {
          "avatar_url": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Avatar Url"
          },
          "discord_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Discord Id"
          },
          "discord_username": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Discord Username"
          },
          "email": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Email"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "is_founder": {
            "title": "Is Founder",
            "type": "boolean"
          }
        },
        "required": [
          "id",
          "discord_id",
          "discord_username",
          "avatar_url",
          "email",
          "is_founder"
        ],
        "title": "UserOut",
        "type": "object"
      },
      "ValidationError": {
        "properties": {
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      }
    },
    "securitySchemes": {
      "HTTPBearer": {
        "scheme": "bearer",
        "type": "http"
      }
    }
  },
  "info": {
    "title": "GridBoss API",
    "version": "0.1.0"
  },
  "openapi": "3.1.0",
  "paths": {
    "/admin/leagues/{league_id}/discord/toggle": {
      "post": {
        "operationId": "admin_toggle_discord_integration_admin_leagues__league_id__discord_toggle_post",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/DiscordToggleRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AdminLeagueSummary"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Admin Toggle Discord Integration",
        "tags": [
          "admin"
        ]
      }
    },
    "/admin/leagues/{league_id}/plan": {
      "post": {
        "operationId": "admin_override_plan_admin_leagues__league_id__plan_post",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PlanOverrideRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AdminLeagueSummary"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Admin Override Plan",
        "tags": [
          "admin"
        ]
      }
    },
    "/admin/search": {
      "get": {
        "operationId": "search_admin_resources_admin_search_get",
        "parameters": [
          {
            "in": "query",
            "name": "query",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Query"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AdminSearchResponse"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Search Admin Resources",
        "tags": [
          "admin"
        ]
      }
    },
    "/audit/logs": {
      "get": {
        "operationId": "list_audit_logs_audit_logs_get",
        "parameters": [
          {
            "in": "query",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          },
          {
            "in": "query",
            "name": "page",
            "required": false,
            "schema": {
              "default": 1,
              "minimum": 1,
              "title": "Page",
              "type": "integer"
            }
          },
          {
            "in": "query",
            "name": "page_size",
            "required": false,
            "schema": {
              "default": 20,
              "maximum": 100,
              "minimum": 1,
              "title": "Page Size",
              "type": "integer"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AuditLogPage"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "List Audit Logs",
        "tags": [
          "audit"
        ]
      }
    },
    "/auth/discord/callback": {
      "get": {
        "operationId": "discord_callback_auth_discord_callback_get",
        "responses": {
          "302": {
            "content": {
              "application/json": {
                "schema": {}
              }
            },
            "description": "Successful Response"
          }
        },
        "summary": "Discord Callback",
        "tags": [
          "auth"
        ]
      }
    },
    "/auth/discord/start": {
      "get": {
        "operationId": "discord_start_auth_discord_start_get",
        "responses": {
          "307": {
            "content": {
              "application/json": {
                "schema": {}
              }
            },
            "description": "Successful Response"
          }
        },
        "summary": "Discord Start",
        "tags": [
          "auth"
        ]
      }
    },
    "/auth/logout": {
      "post": {
        "operationId": "logout_auth_logout_post",
        "responses": {
          "204": {
            "description": "Successful Response"
          }
        },
        "summary": "Logout",
        "tags": [
          "auth"
        ]
      }
    },
    "/auth/me": {
      "get": {
        "operationId": "read_me_auth_me_get",
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/MeResponse"
                }
              }
            },
            "description": "Successful Response"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Read Me",
        "tags": [
          "auth"
        ]
      }
    },
    "/auth/refresh": {
      "post": {
        "operationId": "refresh_token_auth_refresh_post",
        "parameters": [
          {
            "in": "cookie",
            "name": "gb_refresh_token",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Gb Refresh Token"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/TokenResponse"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "summary": "Refresh Token",
        "tags": [
          "auth"
        ]
      }
    },
    "/billing/checkout": {
      "post": {
        "operationId": "create_checkout_session_billing_checkout_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CheckoutRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CheckoutResponse"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Create Checkout Session",
        "tags": [
          "billing"
        ]
      }
    },
    "/billing/overview": {
      "get": {
        "operationId": "read_billing_overview_billing_overview_get",
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/BillingOverviewResponse"
                }
              }
            },
            "description": "Successful Response"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Read Billing Overview",
        "tags": [
          "billing"
        ]
      }
    },
    "/billing/portal": {
      "post": {
        "operationId": "create_portal_session_billing_portal_post",
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PortalResponse"
                }
              }
            },
            "description": "Successful Response"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Create Portal Session",
        "tags": [
          "billing"
        ]
      }
    },
    "/drivers/{driver_id}": {
      "delete": {
        "operationId": "delete_driver_drivers__driver_id__delete",
        "parameters": [
          {
            "in": "path",
            "name": "driver_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Driver Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Delete Driver",
        "tags": [
          "drivers"
        ]
      },
      "patch": {
        "operationId": "update_driver_drivers__driver_id__patch",
        "parameters": [
          {
            "in": "path",
            "name": "driver_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Driver Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/DriverUpdate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/DriverRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Update Driver",
        "tags": [
          "drivers"
        ]
      }
    },
    "/events/{event_id}": {
      "delete": {
        "operationId": "cancel_event_events__event_id__delete",
        "parameters": [
          {
            "in": "path",
            "name": "event_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Event Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Cancel Event",
        "tags": [
          "events"
        ]
      },
      "get": {
        "operationId": "get_event_events__event_id__get",
        "parameters": [
          {
            "in": "path",
            "name": "event_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Event Id",
              "type": "string"
            }
          },
          {
            "in": "query",
            "name": "tz",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Tz"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/EventRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Get Event",
        "tags": [
          "events"
        ]
      },
      "patch": {
        "operationId": "update_event_events__event_id__patch",
        "parameters": [
          {
            "in": "path",
            "name": "event_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Event Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/EventUpdate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/EventRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Update Event",
        "tags": [
          "events"
        ]
      }
    },
    "/events/{event_id}/results": {
      "get": {
        "operationId": "read_results_events__event_id__results_get",
        "parameters": [
          {
            "in": "path",
            "name": "event_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Event Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/EventResultsRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Read Results",
        "tags": [
          "results"
        ]
      },
      "post": {
        "operationId": "submit_results_events__event_id__results_post",
        "parameters": [
          {
            "in": "path",
            "name": "event_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Event Id",
              "type": "string"
            }
          },
          {
            "in": "header",
            "name": "Idempotency-Key",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Idempotency-Key"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ResultSubmission"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/EventResultsRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Submit Results",
        "tags": [
          "results"
        ]
      }
    },
    "/healthz": {
      "get": {
        "description": "Lightweight health probe.",
        "operationId": "healthz_healthz_get",
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "additionalProperties": {
                    "type": "string"
                  },
                  "title": "Response Healthz Healthz Get",
                  "type": "object"
                }
              }
            },
            "description": "Successful Response"
          }
        },
        "summary": "Healthz",
        "tags": [
          "health"
        ]
      }
    },
    "/leagues": {
      "get": {
        "operationId": "list_leagues_leagues_get",
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "items": {
                    "$ref": "#/components/schemas/LeagueRead"
                  },
                  "title": "Response List Leagues Leagues Get",
                  "type": "array"
                }
              }
            },
            "description": "Successful Response"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "List Leagues",
        "tags": [
          "leagues"
        ]
      },
      "post": {
        "operationId": "create_league_leagues_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/LeagueCreate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/LeagueRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Create League",
        "tags": [
          "leagues"
        ]
      }
    },
    "/leagues/{league_id}": {
      "delete": {
        "operationId": "delete_league_leagues__league_id__delete",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Delete League",
        "tags": [
          "leagues"
        ]
      },
      "get": {
        "operationId": "get_league_leagues__league_id__get",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/LeagueRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Get League",
        "tags": [
          "leagues"
        ]
      },
      "patch": {
        "operationId": "update_league_leagues__league_id__patch",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/LeagueUpdate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/LeagueRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Update League",
        "tags": [
          "leagues"
        ]
      }
    },
    "/leagues/{league_id}/discord/link": {
      "post": {
        "operationId": "link_discord_integration_leagues__league_id__discord_link_post",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/DiscordLinkRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/DiscordIntegrationRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Link Discord Integration",
        "tags": [
          "discord"
        ]
      }
    },
    "/leagues/{league_id}/discord/test": {
      "post": {
        "operationId": "trigger_discord_test_leagues__league_id__discord_test_post",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "202": {
            "content": {
              "application/json": {
                "schema": {
                  "additionalProperties": {
                    "type": "string"
                  },
                  "title": "Response Trigger Discord Test Leagues  League Id  Discord Test Post",
                  "type": "object"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Trigger Discord Test",
        "tags": [
          "discord"
        ]
      }
    },
    "/leagues/{league_id}/drivers": {
      "get": {
        "operationId": "list_drivers_leagues__league_id__drivers_get",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "items": {
                    "$ref": "#/components/schemas/DriverRead"
                  },
                  "title": "Response List Drivers Leagues  League Id  Drivers Get",
                  "type": "array"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "List Drivers",
        "tags": [
          "drivers"
        ]
      },
      "post": {
        "operationId": "bulk_create_drivers_leagues__league_id__drivers_post",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/DriverBulkCreate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "content": {
              "application/json": {
                "schema": {
                  "items": {
                    "$ref": "#/components/schemas/DriverRead"
                  },
                  "title": "Response Bulk Create Drivers Leagues  League Id  Drivers Post",
                  "type": "array"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Bulk Create Drivers",
        "tags": [
          "drivers"
        ]
      }
    },
    "/leagues/{league_id}/events": {
      "get": {
        "operationId": "list_events_leagues__league_id__events_get",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          },
          {
            "in": "query",
            "name": "status",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Status"
            }
          },
          {
            "in": "query",
            "name": "tz",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Tz"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "items": {
                    "$ref": "#/components/schemas/EventRead"
                  },
                  "title": "Response List Events Leagues  League Id  Events Get",
                  "type": "array"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "List Events",
        "tags": [
          "events"
        ]
      },
      "post": {
        "operationId": "create_event_leagues__league_id__events_post",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/EventCreate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/EventRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Create Event",
        "tags": [
          "events"
        ]
      }
    },
    "/leagues/{league_id}/memberships": {
      "get": {
        "operationId": "list_memberships_leagues__league_id__memberships_get",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "items": {
                    "$ref": "#/components/schemas/MembershipRead"
                  },
                  "title": "Response List Memberships Leagues  League Id  Memberships Get",
                  "type": "array"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "List Memberships",
        "tags": [
          "memberships"
        ]
      },
      "post": {
        "operationId": "create_membership_leagues__league_id__memberships_post",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/MembershipCreate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/MembershipRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Create Membership",
        "tags": [
          "memberships"
        ]
      }
    },
    "/leagues/{league_id}/memberships/{membership_id}": {
      "delete": {
        "operationId": "delete_membership_leagues__league_id__memberships__membership_id__delete",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          },
          {
            "in": "path",
            "name": "membership_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Membership Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Delete Membership",
        "tags": [
          "memberships"
        ]
      },
      "patch": {
        "operationId": "update_membership_leagues__league_id__memberships__membership_id__patch",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          },
          {
            "in": "path",
            "name": "membership_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Membership Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/MembershipUpdate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/MembershipRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Update Membership",
        "tags": [
          "memberships"
        ]
      }
    },
    "/leagues/{league_id}/points-schemes": {
      "get": {
        "operationId": "list_points_schemes_leagues__league_id__points_schemes_get",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "items": {
                    "$ref": "#/components/schemas/PointsSchemeRead"
                  },
                  "title": "Response List Points Schemes Leagues  League Id  Points Schemes Get",
                  "type": "array"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "List Points Schemes",
        "tags": [
          "points"
        ]
      },
      "post": {
        "operationId": "create_points_scheme_leagues__league_id__points_schemes_post",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PointsSchemeCreate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PointsSchemeRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Create Points Scheme",
        "tags": [
          "points"
        ]
      }
    },
    "/leagues/{league_id}/seasons": {
      "get": {
        "operationId": "list_seasons_leagues__league_id__seasons_get",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "items": {
                    "$ref": "#/components/schemas/SeasonRead"
                  },
                  "title": "Response List Seasons Leagues  League Id  Seasons Get",
                  "type": "array"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "List Seasons",
        "tags": [
          "seasons"
        ]
      },
      "post": {
        "operationId": "create_season_leagues__league_id__seasons_post",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SeasonCreate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/SeasonRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Create Season",
        "tags": [
          "seasons"
        ]
      }
    },
    "/leagues/{league_id}/standings": {
      "get": {
        "operationId": "read_standings_leagues__league_id__standings_get",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          },
          {
            "in": "query",
            "name": "seasonId",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "format": "uuid",
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Seasonid"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/SeasonStandingsRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Read Standings",
        "tags": [
          "standings"
        ]
      }
    },
    "/leagues/{league_id}/teams": {
      "get": {
        "operationId": "list_teams_leagues__league_id__teams_get",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "items": {
                    "$ref": "#/components/schemas/TeamRead"
                  },
                  "title": "Response List Teams Leagues  League Id  Teams Get",
                  "type": "array"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "List Teams",
        "tags": [
          "teams"
        ]
      },
      "post": {
        "operationId": "create_team_leagues__league_id__teams_post",
        "parameters": [
          {
            "in": "path",
            "name": "league_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "League Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/TeamCreate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/TeamRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Create Team",
        "tags": [
          "teams"
        ]
      }
    },
    "/points-schemes/{scheme_id}": {
      "delete": {
        "operationId": "delete_points_scheme_points_schemes__scheme_id__delete",
        "parameters": [
          {
            "in": "path",
            "name": "scheme_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Scheme Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Delete Points Scheme",
        "tags": [
          "points"
        ]
      },
      "patch": {
        "operationId": "update_points_scheme_points_schemes__scheme_id__patch",
        "parameters": [
          {
            "in": "path",
            "name": "scheme_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Scheme Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PointsSchemeUpdate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PointsSchemeRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Update Points Scheme",
        "tags": [
          "points"
        ]
      }
    },
    "/readyz": {
      "get": {
        "operationId": "readyz_readyz_get",
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "title": "Response Readyz Readyz Get",
                  "type": "object"
                }
              }
            },
            "description": "Successful Response"
          }
        },
        "summary": "Readyz",
        "tags": [
          "health"
        ]
      }
    },
    "/seasons/{season_id}": {
      "patch": {
        "operationId": "update_season_seasons__season_id__patch",
        "parameters": [
          {
            "in": "path",
            "name": "season_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Season Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SeasonUpdate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/SeasonRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Update Season",
        "tags": [
          "seasons"
        ]
      }
    },
    "/teams/{team_id}": {
      "delete": {
        "operationId": "delete_team_teams__team_id__delete",
        "parameters": [
          {
            "in": "path",
            "name": "team_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Team Id",
              "type": "string"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Delete Team",
        "tags": [
          "teams"
        ]
      },
      "patch": {
        "operationId": "update_team_teams__team_id__patch",
        "parameters": [
          {
            "in": "path",
            "name": "team_id",
            "required": true,
            "schema": {
              "format": "uuid",
              "title": "Team Id",
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/TeamUpdate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/TeamRead"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "security": [
          {
            "HTTPBearer": []
          }
        ],
        "summary": "Update Team",
        "tags": [
          "teams"
        ]
      }
    },
    "/webhooks/stripe": {
      "post": {
        "operationId": "stripe_webhook_webhooks_stripe_post",
        "parameters": [
          {
            "in": "header",
            "name": "Stripe-Signature",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Stripe-Signature"
            }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "additionalProperties": {
                    "type": "string"
                  },
                  "title": "Response Stripe Webhook Webhooks Stripe Post",
                  "type": "object"
                }
              }
            },
            "description": "Successful Response"
          },
          "422": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            },
            "description": "Validation Error"
          }
        },
        "summary": "Stripe Webhook",
        "tags": [
          "webhooks"
        ]
      }
    }
  }
}
```
