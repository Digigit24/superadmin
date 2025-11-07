PERMISSION_SCHEMA = {
    "crm": {
        "label": "CRM",
        "resources": {
            "leads": {
                "label": "Leads",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "export": {"type": "scope", "options": ["own", "team", "all"]}
                }
            },
            "activities": {
                "label": "Activities",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            },
            "payments": {
                "label": "Payments",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            }
        }
    },
    "whatsapp": {
        "label": "WhatsApp",
        "resources": {
            "messages": {
                "label": "Messages",
                "actions": {
                    "send": {"type": "boolean"},
                    "view": {"type": "boolean"},
                    "delete": {"type": "boolean"}
                }
            },
            "templates": {
                "label": "Templates",
                "actions": {
                    "view": {"type": "boolean"},
                    "create": {"type": "boolean"},
                    "edit": {"type": "boolean"},
                    "delete": {"type": "boolean"}
                }
            }
        }
    },
    "meetings": {
        "label": "Meetings",
        "resources": {
            "meetings": {
                "label": "Meetings",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "scope", "options": ["own", "team", "all"]},
                    "cancel": {"type": "scope", "options": ["own", "team", "all"]}
                }
            }
        }
    },
    "tasks": {
        "label": "Tasks",
        "resources": {
            "tasks": {
                "label": "Tasks",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "scope", "options": ["own", "team", "all"]},
                    "assign": {"type": "boolean"}
                }
            }
        }
    }
}

SUBSCRIPTION_STATUS_CHOICES = [
    ('TRIAL', 'Trial'),
    ('ACTIVE', 'Active'),
    ('PAST_DUE', 'Past Due'),
    ('CANCELLED', 'Cancelled'),
    ('EXPIRED', 'Expired'),
]

BILLING_CYCLE_CHOICES = [
    ('MONTHLY', 'Monthly'),
    ('YEARLY', 'Yearly'),
]

INVOICE_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('PAID', 'Paid'),
    ('FAILED', 'Failed'),
]
