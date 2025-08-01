#!/bin/bash

PROFILE=${1:-default}
PROFILE_ARG=""
if [ "$PROFILE" != "default" ]; then
  PROFILE_ARG="--profile $PROFILE"
fi

echo "🔐 Updating Meetup API credentials using profile: $PROFILE..."

read -p "Enter MEETUP_PRO_URLNAME: " PRO_URLNAME
read -s -p "Enter MEETUP_ACCESS_TOKEN: " ACCESS_TOKEN
echo
read -s -p "Enter MEETUP_CLIENT_SECRET: " CLIENT_SECRET
echo

SECRET_JSON=$(cat <<EOF
{
  "MEETUP_CLIENT_SECRET": "$CLIENT_SECRET",
  "MEETUP_ACCESS_TOKEN": "$ACCESS_TOKEN",
  "MEETUP_PRO_URLNAME": "$PRO_URLNAME"
}
EOF
)

if aws secretsmanager update-secret \
  --secret-id "meetup-dashboard/credentials" \
  --secret-string "$SECRET_JSON" $PROFILE_ARG > /dev/null 2>&1; then
  echo "✅ Secret updated successfully!"
else
  echo "❌ Error updating secret"
  exit 1
fi