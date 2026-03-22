CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TYPE fuel_type AS ENUM ('diesel', 'benzin', 'autogas', 'strom');
CREATE TYPE transport_mode AS ENUM ('car', 'foot', 'bike', 'transit');

CREATE TABLE app_user (
    id UUID PRIMARY KEY,
    home_location GEOGRAPHY(POINT, 4326) NOT NULL,
    transport_mode transport_mode NOT NULL DEFAULT 'car',
    vehicle_consumption_per_100km NUMERIC(5, 2) CHECK (vehicle_consumption_per_100km > 0),
    fuel_type fuel_type,
    transit_cost_per_km_eur NUMERIC(5, 2) CHECK (transit_cost_per_km_eur >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE product (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    brand TEXT,
    category TEXT NOT NULL,
    canonical_unit TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE store (
    id UUID PRIMARY KEY,
    chain TEXT NOT NULL,
    name TEXT,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    address TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_store_location_gist ON store USING GIST (location);

CREATE TABLE store_product_price (
    id UUID PRIMARY KEY,
    store_id UUID NOT NULL REFERENCES store(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    price_eur NUMERIC(10, 2) NOT NULL CHECK (price_eur >= 0),
    package_quantity NUMERIC(10, 3),
    package_unit TEXT,
    in_stock BOOLEAN NOT NULL DEFAULT TRUE,
    price_date DATE NOT NULL,
    source TEXT NOT NULL,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (store_id, product_id, price_date)
);

CREATE INDEX idx_price_date ON store_product_price(price_date);
CREATE INDEX idx_price_store_product ON store_product_price(store_id, product_id);

CREATE TABLE fuel_price (
    id UUID PRIMARY KEY,
    fuel_type fuel_type NOT NULL,
    price_eur_per_unit NUMERIC(6, 3) NOT NULL CHECK (price_eur_per_unit > 0),
    region_code TEXT,
    source TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_fuel_price_type_time ON fuel_price(fuel_type, observed_at DESC);

CREATE TABLE shopping_list (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT 'Meine Liste',
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE shopping_list_item (
    id UUID PRIMARY KEY,
    shopping_list_id UUID NOT NULL REFERENCES shopping_list(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES product(id),
    quantity NUMERIC(10, 3) NOT NULL CHECK (quantity > 0),
    unit TEXT NOT NULL,
    note TEXT
);

CREATE INDEX idx_list_items_list ON shopping_list_item(shopping_list_id);
