# apps/common/constants.py

PERMISSION_SCHEMA = {
    "admin": {
        "label": "Administration",
        "resources": {
            "full_access": {
                "label": "Full Admin Access",
                "actions": {
                    "enabled": {"type": "boolean"}
                }
            },
            "users": {
                "label": "Users",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            },
            "roles": {
                "label": "Roles & Permissions",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            },
            "settings": {
                "label": "Tenant Settings",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]}
                }
            }
        }
    },
    "hms": {
        "label": "Hospital Management",
        "resources": {
            "hospital": {
                "label": "Hospital Configuration",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "edit_config": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            },
            "patients": {
                "label": "Patients",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "export": {"type": "scope", "options": ["own", "team", "all"]}
                }
            },
            "doctors": {
                "label": "Doctors & Specialties",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "export": {"type": "scope", "options": ["own", "team", "all"]},
                    "set_availability": {"type": "scope", "options": ["own", "team", "all"]}
                }
            },
            "appointments": {
                "label": "Appointments",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "cancel": {"type": "scope", "options": ["own", "team", "all"]},
                    "reschedule": {"type": "scope", "options": ["own", "team", "all"]}
                }
            },
            "opd": {
                "label": "OPD",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "export": {"type": "scope", "options": ["own", "team", "all"]},
                    "consult": {"type": "scope", "options": ["own", "team", "all"]},
                    "bill": {"type": "scope", "options": ["own", "team", "all"]},
                    "settings": {"type": "scope", "options": ["own", "team", "all"]}
                }
            },
            "ipd": {
                "label": "IPD",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "export": {"type": "scope", "options": ["own", "team", "all"]},
                    "admit": {"type": "boolean"},
                    "discharge": {"type": "scope", "options": ["own", "team", "all"]},
                    "transfer": {"type": "scope", "options": ["own", "team", "all"]},
                    "bill": {"type": "scope", "options": ["own", "team", "all"]}
                }
            },
            "diagnostics": {
                "label": "Diagnostics",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "export": {"type": "scope", "options": ["own", "team", "all"]},
                    "order": {"type": "boolean"},
                    "report": {"type": "scope", "options": ["own", "team", "all"]},
                    "approve": {"type": "scope", "options": ["own", "team", "all"]}
                }
            },
            "pharmacy": {
                "label": "Pharmacy",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "export": {"type": "scope", "options": ["own", "team", "all"]},
                    "sell": {"type": "boolean"},
                    "stock_adjust": {"type": "scope", "options": ["own", "team", "all"]},
                    "statistics": {"type": "scope", "options": ["own", "team", "all"]}
                }
            },
            "payments": {
                "label": "Payments",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "export": {"type": "scope", "options": ["own", "team", "all"]},
                    "refund": {"type": "scope", "options": ["own", "team", "all"]},
                    "reconcile": {"type": "scope", "options": ["own", "team", "all"]}
                }
            },
            "services": {
                "label": "Services",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            },
            "orders": {
                "label": "Orders & Razorpay",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "pay": {"type": "scope", "options": ["own", "team", "all"]},
                    "refund": {"type": "scope", "options": ["own", "team", "all"]}
                }
            },
            "panchakarma": {
                "label": "Panchakarma",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            }
        }
    },
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
            "statuses": {
                "label": "Lead Statuses",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            },
            "tasks": {
                "label": "Tasks",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "assign": {"type": "boolean"}
                }
            },
            "meetings": {
                "label": "Meetings",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"},
                    "cancel": {"type": "scope", "options": ["own", "team", "all"]}
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
            },
            "settings": {
                "label": "CRM Settings",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]}
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
                    "create": {"type": "boolean"},
                    "edit": {"type": "boolean"},
                    "delete": {"type": "boolean"}
                }
            },
            "templates": {
                "label": "Templates",
                "actions": {
                    "view": {"type": "boolean"},
                    "create": {"type": "boolean"},
                    "edit": {"type": "boolean"},
                    "delete": {"type": "boolean"},
                    # Enforced by WhatsAppTemplateSendProxyView and
                    # WhatsAppTemplateBulkSendProxyView
                    # (permission_action='send'). Distinct from
                    # whatsapp.messages.send, which is a different resource and
                    # a different view — one sends a free-form reply inside the
                    # 24-hour window, this one sends an approved template and is
                    # the only way to open a conversation outside it.
                    "send": {"type": "boolean"}
                }
            },
            "contacts": {
                "label": "Contacts",
                # Enforced by the contacts, contact-group and label proxy views
                # in digicrm/whatsapp_integration/views.py, all of which declare
                # permission_resource='contacts'. Every action here is reachable:
                # view (GET list/detail, import status), create (POST create,
                # POST import), edit (PUT/PATCH detail, add/remove group
                # members), delete (DELETE detail).
                "actions": {
                    "view": {"type": "boolean"},
                    "create": {"type": "boolean"},
                    "edit": {"type": "boolean"},
                    "delete": {"type": "boolean"}
                }
            },
            "campaigns": {
                "label": "Campaigns",
                "actions": {
                    "view": {"type": "boolean"},
                    "create": {"type": "boolean"},
                    "edit": {"type": "boolean"},
                    "delete": {"type": "boolean"}
                }
            },
            "sequences": {
                "label": "Sequences",
                "actions": {
                    "view": {"type": "boolean"},
                    "create": {"type": "boolean"},
                    "edit": {"type": "boolean"},
                    "delete": {"type": "boolean"}
                }
            },
            "settings": {
                "label": "WhatsApp Settings",
                "actions": {
                    "view": {"type": "boolean"},
                    "create": {"type": "boolean"},
                    "edit": {"type": "boolean"},
                    "delete": {"type": "boolean"}
                }
            }
        }
    },
    "integrations": {
        "label": "Integrations",
        "resources": {
            "providers": {
                "label": "Providers",
                "actions": {"view": {"type": "boolean"}}
            },
            "connections": {
                "label": "Connections",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            },
            "workflows": {
                "label": "Workflows",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            }
        }
    },
    "telephony": {
        "label": "Telephony",
        "resources": {
            "calls": {
                "label": "Calls",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            },
            "sms": {
                "label": "SMS",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"}
                }
            },
            "agents": {
                "label": "Agents",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
                    "delete": {"type": "boolean"}
                }
            },
            "callbacks": {
                "label": "Callbacks",
                "actions": {"view": {"type": "scope", "options": ["own", "team", "all"]}}
            },
            "settings": {
                "label": "Telephony Settings",
                "actions": {
                    "view": {"type": "scope", "options": ["own", "team", "all"]},
                    "create": {"type": "boolean"},
                    "edit": {"type": "scope", "options": ["own", "team", "all"]},
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
