# Notification Rollout

We want strength-3 coverage because bugs keep showing up only when three knobs align.

Relevant factors:

- channel: email, sms, push
- audience: new_user, active_user, dormant_user
- locale: en, fr
- quiet_hours: enabled, disabled
- template_family: welcome, promo

Rules:

- welcome messages are only for new users
- sms does not use the welcome template
- dormant users on push must respect quiet hours
