# DIG Salesforce CLI helpers
# Usage examples:
#   make org
#   make dig-validate
#   make dig-deploy
#   make dig-retrieve

SHELL := /bin/bash

ORG ?= deafingov
SRC_DIR ?= dig-src
MANIFEST ?= manifest/dig.xml

.PHONY: help org whoami list \
        dig-validate dig-deploy dig-retrieve dig-pull \
        deploy-governance deploy-membership \
        force-validate force-deploy \
        clean

help:
	@echo "Targets:"
	@echo "  make org            - open DIG org in browser"
	@echo "  make whoami         - show current default org + basic org display"
	@echo "  make list           - list authorized orgs"
	@echo "  make dig-retrieve   - retrieve using $(MANIFEST)"
	@echo "  make dig-validate   - dry-run deploy from $(SRC_DIR)"
	@echo "  make dig-deploy     - deploy from $(SRC_DIR)"
	@echo "  make dig-pull       - pull tracked changes from org (if source tracking)"
	@echo "  make deploy-governance - deploy governance MVP slice manifest"
	@echo "  make deploy-membership - deploy membership core slice manifest"
	@echo "  make force-validate - dry-run deploy from force-app (legacy / noisy)"
	@echo "  make force-deploy   - deploy from force-app (legacy / noisy)"
	@echo ""
	@echo "Vars:"
	@echo "  ORG=deafingov SRC_DIR=dig-src MANIFEST=manifest/dig.xml"

org:
	sf org open --target-org $(ORG)

whoami:
	sf config get target-org || true
	sf org display --target-org $(ORG)

list:
	sf org list

dig-retrieve:
	sf project retrieve start --target-org $(ORG) --manifest $(MANIFEST)

dig-validate:
	sf project deploy start --target-org $(ORG) --source-dir $(SRC_DIR) --dry-run

dig-deploy:
	sf project deploy start --target-org $(ORG) --source-dir $(SRC_DIR)

deploy-governance:
	sf project deploy start --target-org $(ORG) --manifest manifest/governance-mvp.xml

deploy-membership:
	sf project deploy start --target-org $(ORG) --manifest manifest/membership-core.xml

dig-pull:
	sf project pull --target-org $(ORG)

# Legacy targets (useful while transitioning; can be removed later)
force-validate:
	sf project deploy start --target-org $(ORG) --source-dir force-app --dry-run

force-deploy:
	sf project deploy start --target-org $(ORG) --source-dir force-app

clean:
	rm -rf .sf .sfdx
