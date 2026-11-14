-- Listings found on the portals.
CREATE TABLE listings (
    id bigserial PRIMARY KEY,
    source text NOT NULL,                 -- flatfox, anibis, immoscout24, homegate, comparis, newhome
    source_id text NOT NULL,
    url text NOT NULL,
    title text NOT NULL,
    description text NOT NULL DEFAULT '',
    rent numeric, rooms numeric, area numeric,
    zipcode integer, city text NOT NULL DEFAULT '', street text NOT NULL DEFAULT '',
    lat double precision, lon double precision,
    image_url text NOT NULL DEFAULT '',
    published_at timestamptz,
    first_seen timestamptz NOT NULL DEFAULT now(),
    fingerprint text,                     -- same flat on several portals -> same fingerprint
    duplicate_of bigint REFERENCES listings(id),
    matched boolean NOT NULL,
    zone integer,                         -- position of the zone (1 = most wanted), NULL = outside / unknown
    notified_at timestamptz,
    status text NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'favorite', 'applied', 'hidden')),
    UNIQUE (source, source_id)
);
CREATE INDEX listings_fingerprint ON listings (fingerprint);
CREATE INDEX listings_browse ON listings (matched, status) WHERE duplicate_of IS NULL;

-- Small key/value store for the job (e.g. which area each source last searched).
CREATE TABLE state (
    key text PRIMARY KEY,
    value text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Search criteria, edited on the settings page. Exactly one row.
CREATE TABLE settings (
    id integer PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    min_rooms numeric NOT NULL DEFAULT 0,
    max_rooms numeric NOT NULL DEFAULT 0,      -- 0 = no limit
    min_rent numeric NOT NULL DEFAULT 0,
    max_rent numeric NOT NULL DEFAULT 0,       -- 0 = no limit
    min_area numeric NOT NULL DEFAULT 0,
    exclude_keywords text[] NOT NULL DEFAULT '{}',
    anibis_urls text[] NOT NULL DEFAULT '{}',
    notify_to text NOT NULL DEFAULT '',
    updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO settings (id) VALUES (1);

-- Where to live: zones in order of preference, each a list of postcodes.
CREATE TABLE zones (
    id serial PRIMARY KEY,
    position integer NOT NULL UNIQUE,
    name text NOT NULL
);
CREATE TABLE zone_npas (
    zone_id integer NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    npa integer NOT NULL UNIQUE
);
