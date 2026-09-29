$ErrorActionPreference = 'Stop'

$workspace = (Get-Location).Path
$collectionRoot = Join-Path $workspace 'postman\collections\New Collection\Community Emergency Responce'
$archiveRoot = Join-Path $workspace 'postman-archive\pre-sos-collection-rebuild'

if (-not (Test-Path -LiteralPath $collectionRoot)) {
    throw "Collection root not found: $collectionRoot"
}
if (Test-Path -LiteralPath $archiveRoot) {
    throw "Archive target already exists: $archiveRoot"
}

New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
Copy-Item -LiteralPath $collectionRoot -Destination (Join-Path $archiveRoot 'Community Emergency Responce') -Recurse -Force
foreach ($legacy in @(
    'postman\Emergency_Response_System.postman_collection.json',
    'postman\Community_Emergency_Response_M1_M2.postman_collection.json'
)) {
    if (Test-Path -LiteralPath (Join-Path $workspace $legacy)) {
        Copy-Item -LiteralPath (Join-Path $workspace $legacy) -Destination $archiveRoot -Force
    }
}

function Write-Utf8([string] $path, [string] $content) {
    $parent = Split-Path -Parent $path
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding($false)))
}

function Add-Request(
    [System.Collections.Generic.List[object]] $list,
    [string] $file,
    [string] $method,
    [string] $url,
    [string] $auth,
    [string] $body,
    [string] $description
) {
    $list.Add([ordered]@{
        File = $file
        Method = $method
        Url = $url
        Auth = $auth
        Body = $body
        Description = $description
    })
}

$folders = [System.Collections.Generic.List[object]]::new()

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1-Register.request.yaml' 'POST' '{{base_url}}/api/v1/auth/register/' '' @'
{
  "username": "{{resident_username}}",
  "email": "{{resident_email}}",
  "phone": "{{resident_phone}}",
  "password": "{{resident_password}}"
}
'@ ''
Add-Request $r '2-login.request.yaml' 'POST' '{{base_url}}/api/v1/auth/login/' '' @'
{
  "username": "{{resident_username}}",
  "password": "{{resident_password}}"
}
'@ ''
Add-Request $r '3-Get Profile.request.yaml' 'GET' '{{base_url}}/api/v1/auth/me/' 'resident_token' '' ''
Add-Request $r '4-Refresh token.request.yaml' 'POST' '{{base_url}}/api/v1/token/refresh/' '' @'
{
  "refresh": "{{refresh_token}}"
}
'@ 'SimpleJWT expects the refresh token under the refresh field.'
$folders.Add([ordered]@{Name='1-Authentication'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r 'Update profile.request.yaml' 'PUT' '{{base_url}}/api/v1/auth/profile/update/' 'resident_token' @'
{
  "username": "{{resident_username}}",
  "email": "{{resident_email}}"
}
'@ ''
Add-Request $r 'Delete profile.request.yaml' 'DELETE' '{{base_url}}/api/v1/auth/profile/delete/' 'resident_token' '' ''
$folders.Add([ordered]@{Name='2-Profile'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1- Add gated society.request.yaml' 'POST' '{{base_url}}/api/societies/' 'admin_token' @'
{
  "society_name": "{{society_name}}",
  "owner_name": "{{society_owner_name}}",
  "incharge": "{{society_incharge}}",
  "address": "{{society_address}}"
}
'@ ''
Add-Request $r '2-Get gated society.request.yaml' 'GET' '{{base_url}}/api/societies/list/' 'admin_token' '' ''
Add-Request $r '3-Update gated society.request.yaml' 'PUT' '{{base_url}}/api/societies/update/{{society_id}}/' 'admin_token' @'
{
  "society_name": "{{society_name}}",
  "owner_name": "{{society_owner_name}}",
  "incharge": "{{society_incharge}}",
  "address": "{{society_address}}"
}
'@ ''
Add-Request $r '4-Delete gated society.request.yaml' 'DELETE' '{{base_url}}/api/societies/delete/{{society_id}}/' 'admin_token' '' ''
$folders.Add([ordered]@{Name='3-Gated society'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1-Create Flat.request.yaml' 'POST' '{{base_url}}/api/v1/flats/' 'admin_token' @'
{
  "flat_number": "{{flat_number}}",
  "owner_name": "{{flat_owner_name}}",
  "floor": {{flat_floor}},
  "society_name": "{{society_name}}"
}
'@ ''
Add-Request $r '2-List Flat.request.yaml' 'GET' '{{base_url}}/api/v1/flats/list/' 'admin_token' '' ''
Add-Request $r '3-Get Flat.request.yaml' 'GET' '{{base_url}}/api/v1/flats/{{flat_id}}/' 'resident_token' '' ''
Add-Request $r '4-Update Flat.request.yaml' 'PUT' '{{base_url}}/api/v1/flats/update/{{flat_id}}/' 'admin_token' @'
{
  "flat_number": "{{flat_number}}",
  "owner_name": "{{flat_owner_name}}",
  "floor": {{flat_floor}},
  "society_name": "{{society_name}}"
}
'@ ''
Add-Request $r '5-Delete Flat.request.yaml' 'DELETE' '{{base_url}}/api/v1/flats/delete/{{flat_id}}/' 'admin_token' '' ''
$folders.Add([ordered]@{Name='4-Flat Section (Gated society)'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1-invite API.request.yaml' 'POST' '{{base_url}}/api/v1/invite/' '' @'
{
  "email": "{{invite_email}}"
}
'@ ''
Add-Request $r '2-Send OTP.request.yaml' 'POST' '{{base_url}}/api/v1/send-otp/' '' @'
{
  "email": "{{resident_email}}"
}
'@ ''
Add-Request $r '3-OTP verification.request.yaml' 'POST' '{{base_url}}/api/v1/verify-otp/' '' @'
{
  "email": "{{resident_email}}",
  "otp": "{{otp}}"
}
'@ ''
$folders.Add([ordered]@{Name='5-SMTP'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1-Add Emergency Contact.request.yaml' 'POST' '{{base_url}}/api/v1/users/me/emergency-contacts/' 'resident_token' @'
{
  "name": "{{emergency_contact_name}}",
  "email": "{{emergency_contact_email}}",
  "mobile": "{{emergency_contact_mobile}}",
  "relationship": "{{emergency_contact_relationship}}",
  "priority": {{emergency_contact_priority}}
}
'@ ''
Add-Request $r '2-List Emergency Contact.request.yaml' 'GET' '{{base_url}}/api/v1/users/me/emergency-contacts/' 'resident_token' '' ''
Add-Request $r '3-Update Emergency Contact.request.yaml' 'PATCH' '{{base_url}}/api/v1/emergency-contacts/{{contact_id}}/' 'resident_token' @'
{
  "name": "{{emergency_contact_name}}",
  "email": "{{emergency_contact_email}}",
  "mobile": "{{emergency_contact_mobile}}",
  "relationship": "{{emergency_contact_relationship}}",
  "priority": {{emergency_contact_priority}}
}
'@ ''
Add-Request $r '4-Delete Emergency Contact.request.yaml' 'DELETE' '{{base_url}}/api/v1/emergency-contacts/{{contact_id}}/' 'resident_token' '' ''
Add-Request $r '5-Send OTP Contact Verification.request.yaml' 'POST' '{{base_url}}/api/v1/emergency-contacts/{{contact_id}}/send-otp/' 'resident_token' '' ''
Add-Request $r '6-Verify Contact.request.yaml' 'POST' '{{base_url}}/api/v1/emergency-contacts/{{contact_id}}/verify/' 'resident_token' @'
{
  "otp": "{{contact_otp}}"
}
'@ ''
$folders.Add([ordered]@{Name='6- Emergency Contacts'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1-Get SOS configuration.request.yaml' 'GET' '{{base_url}}/api/v1/users/me/sos-config/' 'resident_token' '' ''
Add-Request $r '2-Update SOS configuration.request.yaml' 'PATCH' '{{base_url}}/api/v1/users/me/sos-config/' 'resident_token' @'
{
  "default_category": "{{category_code}}",
  "response_timeout_seconds": {{response_timeout_seconds}},
  "notify_guardians": {{notify_guardians}},
  "notify_security": {{notify_security}},
  "notify_volunteers": {{notify_volunteers}},
  "community_broadcast": {{community_broadcast}},
  "location_sharing": {{location_sharing}}
}
'@ ''
$folders.Add([ordered]@{Name='7-SOS configuration'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1-Emergency categories.request.yaml' 'GET' '{{base_url}}/api/v1/emergency-categories/' 'resident_token' '' ''
Add-Request $r '2-Create SOS incidents.request.yaml' 'POST' '{{base_url}}/api/v1/incidents/' 'resident_token' @'
{
  "category": "{{category_code}}",
  "message": "{{sos_message}}",
  "location": {
    "latitude": {{latitude}},
    "longitude": {{longitude}},
    "accuracy": {{accuracy}}
  },
  "phone": "{{sos_phone}}"
}
'@ ''
Add-Request $r '3-Get My SOS incidents.request.yaml' 'GET' '{{base_url}}/api/v1/incidents/' 'resident_token' '' ''
Add-Request $r '4-Get SOS incident.request.yaml' 'GET' '{{base_url}}/api/v1/incidents/{{incident_id}}/' 'resident_token' '' ''
Add-Request $r '5-Update SOS status.request.yaml' 'PATCH' '{{base_url}}/api/v1/incidents/{{incident_id}}/status/' 'responder_token' @'
{
  "status": "{{incident_status}}",
  "note": "{{status_note}}"
}
'@ ''
Add-Request $r '6-Get SOS Notifications.request.yaml' 'GET' '{{base_url}}/api/v1/incidents/{{incident_id}}/notifications/' 'resident_token' '' ''
Add-Request $r '7-Respond to SOS.request.yaml' 'POST' '{{base_url}}/api/v1/incidents/{{incident_id}}/respond/' 'responder_token' @'
{
  "estimated_arrival_minutes": {{estimated_arrival_minutes}}
}
'@ ''
$folders.Add([ordered]@{Name='8-SOS Management'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1-Update Location.request.yaml' 'POST' '{{base_url}}/api/v1/users/me/location/' 'resident_token' @'
{
  "latitude": {{latitude}},
  "longitude": {{longitude}},
  "accuracy": {{accuracy}}
}
'@ ''
Add-Request $r '2-Get Location.request.yaml' 'GET' '{{base_url}}/api/v1/users/me/location/' 'resident_token' '' ''
$folders.Add([ordered]@{Name='9-Location APIs'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '2-Create SOS Alert.request.yaml' 'POST' '{{base_url}}/api/v1/incidents/sos/' 'resident_token' @'
{
  "category": "{{category_code}}",
  "message": "{{sos_message}}",
  "location": {
    "latitude": {{latitude}},
    "longitude": {{longitude}},
    "accuracy": {{accuracy}}
  },
  "phone": "{{sos_phone}}"
}
'@ 'This endpoint creates the SOS incident and dispatches configured notification channels.'
Add-Request $r '3-Mark Notification read.request.yaml' 'PATCH' '{{base_url}}/api/v1/notifications/{{notification_id}}/read/' 'resident_token' '' ''
Add-Request $r '4-Push Notification.request.yaml' 'POST' '{{base_url}}/api/v1/notifications/send-push/' 'resident_token' @'
{
  "topic": "{{fcm_topic}}",
  "title": "{{notification_title}}",
  "body": "{{notification_body}}",
  "data": {
    "emergency_type": "{{emergency_type}}",
    "incident_id": "{{incident_id}}"
  }
}
'@ ''
Add-Request $r '5-Push Notification Device Token.request.yaml' 'POST' '{{base_url}}/api/v1/notifications/send-push/' 'resident_token' @'
{
  "device_token": "{{fcm_device_token}}",
  "title": "{{notification_title}}",
  "body": "{{notification_body}}",
  "data": {
    "emergency_type": "{{emergency_type}}",
    "incident_id": "{{incident_id}}"
  }
}
'@ ''
Add-Request $r 'Create Notification count.request.yaml' 'GET' '{{base_url}}/api/v1/notifications/count/' 'resident_token' '' ''
$folders.Add([ordered]@{Name='10-Get SOS Notifications'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '2-Send SOS SMS.request.yaml' 'POST' '{{base_url}}/api/v1/send-sos-sms/' 'resident_token' @'
{
  "phone": "{{sos_phone}}",
  "message": "{{sos_message}}"
}
'@ ''
$folders.Add([ordered]@{Name='11-SMS Notification'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1-Send Email.request.yaml' 'POST' '{{base_url}}/api/v1/notifications/send-email/' 'resident_token' @'
{
  "email": "{{notification_email}}",
  "subject": "{{email_subject}}",
  "message": "{{email_message}}"
}
'@ ''
$folders.Add([ordered]@{Name='12-Email Notification'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1-In App Notification.request.yaml' 'GET' '{{base_url}}/api/v1/notifications/' 'resident_token' '' ''
$folders.Add([ordered]@{Name='13-In App Notifications'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1-Route SOS Alert.request.yaml' 'POST' '{{base_url}}/api/v1/alert-routing/route-alert/' 'admin_token' @'
{
  "incident_id": "{{incident_id}}",
  "emergency_type": "{{emergency_type}}"
}
'@ ''
Add-Request $r '2-Get Alert Routes.request.yaml' 'GET' '{{base_url}}/api/v1/alert-routing/routes/?incident_id={{incident_id}}' 'admin_token' '' ''
Add-Request $r '3-Update Guardian Delivery.request.yaml' 'PATCH' '{{base_url}}/api/v1/alert-routing/routes/{{guardian_route_id}}/delivery/' 'admin_token' @'
{
  "delivery_status": "{{guardian_delivery_status}}"
}
'@ ''
Add-Request $r '4-Update Security Delivery.request.yaml' 'PATCH' '{{base_url}}/api/v1/alert-routing/routes/{{security_route_id}}/delivery/' 'admin_token' @'
{
  "delivery_status": "{{security_delivery_status}}"
}
'@ ''
Add-Request $r '5-Update Volunteer Delivery.request.yaml' 'PATCH' '{{base_url}}/api/v1/alert-routing/routes/{{volunteer_route_id}}/delivery/' 'admin_token' @'
{
  "delivery_status": "{{volunteer_delivery_status}}"
}
'@ ''
Add-Request $r '6-Update Volunteer Failed.request.yaml' 'PATCH' '{{base_url}}/api/v1/alert-routing/routes/{{volunteer_route_id}}/delivery/' 'admin_token' @'
{
  "delivery_status": "FAILED"
}
'@ ''
Add-Request $r '7-Response Received.request.yaml' 'PATCH' '{{base_url}}/api/v1/alert-routing/routes/{{route_id}}/response/' 'admin_token' @'
{
  "response_status": "RESPONDED"
}
'@ ''
Add-Request $r '8-Monitor Alert.request.yaml' 'GET' '{{base_url}}/api/v1/alert-routing/monitor/?incident_id={{incident_id}}' 'admin_token' '' ''
$folders.Add([ordered]@{Name='14-Alert Routing and Monitoring'; Requests=$r})

$r = [System.Collections.Generic.List[object]]::new()
Add-Request $r '1-Create Guardian Response Request.request.yaml' 'POST' '{{base_url}}/api/v1/incidents/' 'resident_token' @'
{
  "category": "{{category_code}}",
  "message": "{{sos_message}}",
  "location": {
    "latitude": {{latitude}},
    "longitude": {{longitude}},
    "accuracy": {{accuracy}}
  },
  "phone": "{{sos_phone}}"
}
'@ 'Creating an SOS incident is the backend operation that creates the primary guardian response workflow.'
Add-Request $r '2-Get Guardian Notifications.request.yaml' 'GET' '{{base_url}}/api/v1/notifications/' 'guardian_token' '' ''
Add-Request $r '3-Guardian Respond.request.yaml' 'POST' '{{base_url}}/api/v1/incidents/{{incident_id}}/guardian/respond/' 'guardian_token' '' ''
Add-Request $r '4-Escalate to Secondary Guardian.request.yaml' 'POST' '{{base_url}}/api/v1/incidents/{{incident_id}}/guardian/escalate/' 'resident_token' @'
{
  "level": 2
}
'@ ''
Add-Request $r '5-Escalate to Emergency Contacts.request.yaml' 'POST' '{{base_url}}/api/v1/incidents/{{incident_id}}/guardian/escalate/' 'resident_token' @'
{
  "level": 3
}
'@ ''
Add-Request $r '6-Get Incident History.request.yaml' 'GET' '{{base_url}}/api/v1/incidents/{{incident_id}}/history/' 'resident_token' '' ''
$folders.Add([ordered]@{Name='15-Guardian Escalation work flow'; Requests=$r})

# Remove the old request files from the fifteen requested folders, then write the exact requested structure.
foreach ($folder in $folders) {
    $folderPath = Join-Path $collectionRoot $folder.Name
    if (Test-Path -LiteralPath $folderPath) {
        Get-ChildItem -LiteralPath $folderPath -Filter '*.request.yaml' -File -ErrorAction SilentlyContinue | Remove-Item -Force
    } else {
        New-Item -ItemType Directory -Path $folderPath -Force | Out-Null
    }

    $folderOrder = 1000 + $folders.IndexOf($folder)
    Write-Utf8 (Join-Path $folderPath '.resources\definition.yaml') @"
`$kind: collection
name: $($folder.Name)
order: $folderOrder
"@

    $requestOrder = 1
    foreach ($request in $folder.Requests) {
        $lines = [System.Collections.Generic.List[string]]::new()
        $lines.Add('$kind: http-request')
        if ($request.Description) {
            $lines.Add('description: "' + ($request.Description -replace '"', '\"') + '"')
        }
        $lines.Add('url: "' + $request.Url + '"')
        $lines.Add('method: ' + $request.Method)
        if ($request.Auth) {
            $lines.Add('headers:')
            $lines.Add('  Authorization: Bearer {{' + $request.Auth + '}}')
            if ($request.Body) {
                $lines.Add('  Content-Type: application/json')
            }
        } elseif ($request.Body) {
            $lines.Add('headers:')
            $lines.Add('  Content-Type: application/json')
        }
        if ($request.Body) {
            $lines.Add('body:')
            $lines.Add('  type: json')
            $lines.Add('  content: |-')
            foreach ($bodyLine in ($request.Body.Trim() -split "`r?`n")) {
                $lines.Add('    ' + $bodyLine)
            }
        }
        $lines.Add('order: ' + $requestOrder)
        Write-Utf8 (Join-Path $folderPath $request.File) ($lines -join "`n" )
        $requestOrder++
    }
}

# Keep only the requested 1-15 folders in the active collection. The old extra folder is in the archive.
$extraFolder = Join-Path $collectionRoot '16-M1-M2 Complete'
if (Test-Path -LiteralPath $extraFolder) {
    Remove-Item -LiteralPath $extraFolder -Recurse -Force
}

Write-Utf8 (Join-Path $collectionRoot '.resources\definition.yaml') @'
$kind: collection
name: Community Emergency Responce
order: 1
'@

# Move legacy v2 JSON collections out of the auto-discovered postman directory.
foreach ($legacy in @(
    'postman\Emergency_Response_System.postman_collection.json',
    'postman\Community_Emergency_Response_M1_M2.postman_collection.json'
)) {
    $legacyPath = Join-Path $workspace $legacy
    if (Test-Path -LiteralPath $legacyPath) {
        Move-Item -LiteralPath $legacyPath -Destination $archiveRoot -Force
    }
}

$environment = [ordered]@{
    name = 'Community Emergency Response - Local'
    values = @(
        [ordered]@{key='base_url'; value='http://127.0.0.1:8000'; type='default'; enabled=$true},
        [ordered]@{key='access_token'; value='REPLACE_WITH_ACCESS_TOKEN'; type='secret'; enabled=$true},
        [ordered]@{key='refresh_token'; value='REPLACE_WITH_REFRESH_TOKEN'; type='secret'; enabled=$true},
        [ordered]@{key='resident_token'; value='REPLACE_WITH_RESIDENT_ACCESS_TOKEN'; type='secret'; enabled=$true},
        [ordered]@{key='responder_token'; value='REPLACE_WITH_SECURITY_OR_VOLUNTEER_ACCESS_TOKEN'; type='secret'; enabled=$true},
        [ordered]@{key='guardian_token'; value='REPLACE_WITH_GUARDIAN_ACCESS_TOKEN'; type='secret'; enabled=$true},
        [ordered]@{key='admin_token'; value='REPLACE_WITH_ADMIN_ACCESS_TOKEN'; type='secret'; enabled=$true},
        [ordered]@{key='resident_username'; value='REPLACE_WITH_YOUR_USERNAME'; type='default'; enabled=$true},
        [ordered]@{key='resident_email'; value='REPLACE_WITH_YOUR_EMAIL'; type='default'; enabled=$true},
        [ordered]@{key='resident_phone'; value='REPLACE_WITH_YOUR_MOBILE'; type='default'; enabled=$true},
        [ordered]@{key='resident_password'; value='REPLACE_WITH_YOUR_PASSWORD'; type='secret'; enabled=$true},
        [ordered]@{key='invite_email'; value='REPLACE_WITH_INVITEE_EMAIL'; type='default'; enabled=$true},
        [ordered]@{key='otp'; value='REPLACE_WITH_EMAIL_OTP'; type='default'; enabled=$true},
        [ordered]@{key='contact_otp'; value='REPLACE_WITH_CONTACT_OTP'; type='default'; enabled=$true},
        [ordered]@{key='society_id'; value='1'; type='default'; enabled=$true},
        [ordered]@{key='society_name'; value='REPLACE_WITH_SOCIETY_NAME'; type='default'; enabled=$true},
        [ordered]@{key='society_owner_name'; value='REPLACE_WITH_OWNER_NAME'; type='default'; enabled=$true},
        [ordered]@{key='society_incharge'; value='REPLACE_WITH_INCHARGE'; type='default'; enabled=$true},
        [ordered]@{key='society_address'; value='REPLACE_WITH_SOCIETY_ADDRESS'; type='default'; enabled=$true},
        [ordered]@{key='flat_id'; value='1'; type='default'; enabled=$true},
        [ordered]@{key='flat_number'; value='REPLACE_WITH_FLAT_NUMBER'; type='default'; enabled=$true},
        [ordered]@{key='flat_owner_name'; value='REPLACE_WITH_FLAT_OWNER'; type='default'; enabled=$true},
        [ordered]@{key='flat_floor'; value='1'; type='default'; enabled=$true},
        [ordered]@{key='emergency_contact_name'; value='REPLACE_WITH_CONTACT_NAME'; type='default'; enabled=$true},
        [ordered]@{key='emergency_contact_email'; value='REPLACE_WITH_CONTACT_EMAIL'; type='default'; enabled=$true},
        [ordered]@{key='emergency_contact_mobile'; value='REPLACE_WITH_CONTACT_MOBILE'; type='default'; enabled=$true},
        [ordered]@{key='emergency_contact_relationship'; value='REPLACE_WITH_RELATIONSHIP'; type='default'; enabled=$true},
        [ordered]@{key='emergency_contact_priority'; value='1'; type='default'; enabled=$true},
        [ordered]@{key='category_code'; value='medical'; type='default'; enabled=$true},
        [ordered]@{key='sos_message'; value='REPLACE_WITH_SOS_MESSAGE'; type='default'; enabled=$true},
        [ordered]@{key='sos_phone'; value='REPLACE_WITH_SOS_PHONE'; type='default'; enabled=$true},
        [ordered]@{key='latitude'; value='13.1143'; type='default'; enabled=$true},
        [ordered]@{key='longitude'; value='80.1485'; type='default'; enabled=$true},
        [ordered]@{key='accuracy'; value='8.5'; type='default'; enabled=$true},
        [ordered]@{key='incident_id'; value='1'; type='default'; enabled=$true},
        [ordered]@{key='incident_status'; value='RESPONSE_RECEIVED'; type='default'; enabled=$true},
        [ordered]@{key='status_note'; value='REPLACE_WITH_STATUS_NOTE'; type='default'; enabled=$true},
        [ordered]@{key='estimated_arrival_minutes'; value='5'; type='default'; enabled=$true},
        [ordered]@{key='notification_id'; value='1'; type='default'; enabled=$true},
        [ordered]@{key='fcm_device_token'; value='REPLACE_WITH_FCM_DEVICE_TOKEN'; type='secret'; enabled=$true},
        [ordered]@{key='fcm_topic'; value='emergency_alerts'; type='default'; enabled=$true},
        [ordered]@{key='notification_title'; value='SOS Emergency Alert'; type='default'; enabled=$true},
        [ordered]@{key='notification_body'; value='Resident requested immediate emergency assistance.'; type='default'; enabled=$true},
        [ordered]@{key='emergency_type'; value='medical'; type='default'; enabled=$true},
        [ordered]@{key='notification_email'; value='REPLACE_WITH_NOTIFICATION_EMAIL'; type='default'; enabled=$true},
        [ordered]@{key='email_subject'; value='Emergency Alert'; type='default'; enabled=$true},
        [ordered]@{key='email_message'; value='REPLACE_WITH_EMAIL_MESSAGE'; type='default'; enabled=$true},
        [ordered]@{key='guardian_route_id'; value='1'; type='default'; enabled=$true},
        [ordered]@{key='security_route_id'; value='2'; type='default'; enabled=$true},
        [ordered]@{key='volunteer_route_id'; value='3'; type='default'; enabled=$true},
        [ordered]@{key='route_id'; value='1'; type='default'; enabled=$true},
        [ordered]@{key='guardian_delivery_status'; value='DELIVERED'; type='default'; enabled=$true},
        [ordered]@{key='security_delivery_status'; value='DELIVERED'; type='default'; enabled=$true},
        [ordered]@{key='volunteer_delivery_status'; value='DELIVERED'; type='default'; enabled=$true},
        [ordered]@{key='response_timeout_seconds'; value='60'; type='default'; enabled=$true},
        [ordered]@{key='notify_guardians'; value='true'; type='default'; enabled=$true},
        [ordered]@{key='notify_security'; value='true'; type='default'; enabled=$true},
        [ordered]@{key='notify_volunteers'; value='true'; type='default'; enabled=$true},
        [ordered]@{key='community_broadcast'; value='true'; type='default'; enabled=$true},
        [ordered]@{key='location_sharing'; value='true'; type='default'; enabled=$true}
    )
    _postman_variable_scope = 'environment'
    _postman_exported_using = 'Codex read/write-safe template'
}
Write-Utf8 (Join-Path $workspace 'postman\Community_Emergency_Response.local.environment.json') (($environment | ConvertTo-Json -Depth 6) + "`n")

Write-Output ("Rebuilt {0} folders and {1} requests. Backup: {2}" -f $folders.Count, (($folders | ForEach-Object { $_.Requests.Count } | Measure-Object -Sum).Sum), $archiveRoot)
