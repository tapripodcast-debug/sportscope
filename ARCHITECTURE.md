# Sportscope v2 architecture

## Participation model
A result qualifies only when a participant is matched to the selected entity:
- Country: a national-team alias matches a participant, or participant-level representation metadata explicitly identifies the country.
- Team: the selected team matches a participant.
- Player: the selected player matches a participant.
- State/city: later support must use team/player affiliation or official event representation, not venue location alone.

## Important source constraint
SportsEvents24 documents `country + sport_id` or `tournament_id` queries, not global participant search. Therefore its feed can only be used as a limited candidate source. It cannot guarantee fixtures hosted abroad. This limitation is disclosed in the UI.

## Canonical event model (target)
`event_id`, `sport`, `event_name`, `start_time_utc`, `timezone`, `venue`, `city`, `country`, `tournament`, `participants[]`, `teams[]`, `represented_country`, `status`, `source_url`, `provider_updated_at`, `last_verified_at`, `broadcast_options[]`.

## Target pipeline
Entity resolution -> sport-specific participant schedule connectors -> normalization -> participation verification -> deduplication -> source verification -> sport-wise UI tables -> event/team/player detail pages.
