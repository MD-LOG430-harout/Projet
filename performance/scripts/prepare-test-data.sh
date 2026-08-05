#!/usr/bin/env bash
set -euo pipefail
base_url="${BASE_URL:-http://localhost:8080}"
suffix="$(date +%s)-$RANDOM"
email="phase2-${suffix}@example.test"
password="Stronger123"
register="$(curl -fsS -H 'Content-Type: application/json' -d "{\"email\":\"$email\",\"password\":\"$password\",\"displayName\":\"Phase 2 Test\",\"legalName\":\"Phase 2 Test\",\"address\":{\"line1\":\"123 Rue Test\",\"city\":\"Montreal\",\"province\":\"QC\",\"postalCode\":\"H1A1A1\"},\"identityDocument\":{\"type\":\"driver_license\",\"number\":\"P2-$suffix\"},\"customerType\":\"individual\"}" "$base_url/v1/customers/register")"
customer_id="$(printf '%s' "$register" | sed -n 's/.*"customerId":"\([^"]*\)".*/\1/p')"
login="$(curl -fsS -H 'Content-Type: application/json' -d "{\"email\":\"$email\",\"password\":\"$password\"}" "$base_url/v1/auth/login")"
challenge="$(printf '%s' "$login" | sed -n 's/.*"challengeId":"\([^"]*\)".*/\1/p')"
otp="$(printf '%s' "$login" | sed -n 's/.*"devOtp":"\([^"]*\)".*/\1/p')"
verify="$(curl -fsS -H 'Content-Type: application/json' -d "{\"challengeId\":\"$challenge\",\"otp\":\"$otp\"}" "$base_url/v1/auth/mfa/verify")"
token="$(printf '%s' "$verify" | sed -n 's/.*"sessionToken":"\([^"]*\)".*/\1/p')"
printf 'CUSTOMER_ID=%s\nTOKEN=%s\nOFFER_ID=forfait-5g-20gb\n' "$customer_id" "$token" > performance/results/test-data.env
echo "Created isolated customer $customer_id; credentials were not persisted."
