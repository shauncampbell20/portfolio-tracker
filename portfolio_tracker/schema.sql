DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS transactions;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  tran_date TIMESTAMP NOT NULL,
  symbol TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  share_price REAL NOT NULL,
  FOREIGN KEY (user_id) REFERENCES user (id)
);

CREATE TABLE positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  cost_basis REAL NOT NULL,
  realized_cost_basis REAL NOT NULL,
  realized_value REAL NOT NULL,
  FOREIGN KEY (user_id) REFERENCES user (id)
)