#!/bin/bash

echo "Testing registration with curl..."

# Use a cookie jar to maintain session
COOKIE_JAR="/tmp/test_cookies.txt"
rm -f $COOKIE_JAR

# Step 1: Get the registration page and save cookies
echo "1. Getting registration page..."
RESPONSE=$(curl -s -c $COOKIE_JAR -b $COOKIE_JAR http://localhost:8000/accounts/register/)

# Extract CSRF token
CSRF_TOKEN=$(echo "$RESPONSE" | grep -oP 'name="csrfmiddlewaretoken" value="\K[^"]+')
echo "   CSRF Token: $CSRF_TOKEN"

# Extract CAPTCHA token
CAPTCHA_TOKEN=$(echo "$RESPONSE" | grep -oP 'name="captcha_token" value="\K[^"]+')
echo "   CAPTCHA Token: $CAPTCHA_TOKEN"

# Step 2: Submit the form
echo -e "\n2. Submitting registration form..."
curl -v -X POST http://localhost:8000/accounts/register/ \
  -H "Referer: http://localhost:8000/accounts/register/" \
  -H "Origin: http://localhost:8000" \
  -b $COOKIE_JAR \
  -c $COOKIE_JAR \
  -d "csrfmiddlewaretoken=$CSRF_TOKEN" \
  -d "username=testuser456" \
  -d "password1=TestPass123!" \
  -d "password2=TestPass123!" \
  -d "captcha.x=50" \
  -d "captcha.y=50" \
  -d "captcha_token=$CAPTCHA_TOKEN" \
  -d "captcha_x=" \
  -d "captcha_y=" \
  -d "website=" \
  -d "email_address=" \
  -d "form_timestamp=$(date +%s)" \
  -d "form_hash=test123" \
  2>&1 | grep -E "< HTTP|< Location|CSRF|Invalid CAPTCHA"

echo -e "\nDone!"
rm -f $COOKIE_JAR