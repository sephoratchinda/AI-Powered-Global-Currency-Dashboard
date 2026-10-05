-- Database design (SQLAlchemy creates this automatically; shown for documentation)
CREATE TABLE rates (
  id        INTEGER PRIMARY KEY,
  day       DATE        NOT NULL,
  currency  VARCHAR(3)  NOT NULL,
  per_usd   FLOAT       NOT NULL,          -- units of currency per 1 USD
  CONSTRAINT uq_day_currency UNIQUE (day, currency)
);
CREATE INDEX ix_rates_day ON rates(day);

CREATE TABLE alerts (
  id        INTEGER PRIMARY KEY,
  pair      VARCHAR(7)  NOT NULL,          -- 'USD/INR'
  direction VARCHAR(5)  NOT NULL,          -- 'above' | 'below'
  threshold FLOAT       NOT NULL,
  active    BOOLEAN     DEFAULT TRUE
);
-- Any pair rate = per_usd(quote) / per_usd(base)   (USD stored as 1.0)
