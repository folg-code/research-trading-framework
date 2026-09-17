"""Trading session identifier constants."""

ES_RTH_SESSION_ID = "ES_RTH"
OUTSIDE_RTH_SESSION_ID = "OUTSIDE_RTH"

RESOLVER_OUTPUT_COLUMNS = ("timestamp", "trading_day", "session_id", "is_rth")

# Named-session boolean columns (ADR-MA-015): additive, optional columns a
# resolver's output frame may carry alongside RESOLVER_OUTPUT_COLUMNS, one
# per simultaneously-relevant named intraday session. Consumed via
# TradingSessionMetadata.named_session(name).
SESSION_ASIA_COLUMN = "session_asia"
SESSION_LONDON_COLUMN = "session_london"
SESSION_NEW_YORK_COLUMN = "session_new_york"
