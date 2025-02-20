use mongodb::{Client, Collection, Database};
use once_cell::sync::OnceCell;

#[allow(dead_code)]
#[derive(Debug)]
pub struct MongoDB {
    db: Database,
}

#[allow(dead_code)]
pub static DB_INSTANCE: OnceCell<MongoDB> = OnceCell::new();

impl MongoDB {
    pub async fn connect(uri: &str) -> &MongoDB {
        let client = Client::with_uri_str(uri).await.expect("Cannot connect to database!");
        let db = client.default_database().unwrap();
        let conn = MongoDB { db };
        DB_INSTANCE.set(conn).expect("SET_DB_INSTANCE");
        log::debug!("Connected to database!");
        MongoDB::instance()
    }

    pub fn instance() -> &'static MongoDB {
        DB_INSTANCE.get().unwrap()
    }

    pub fn collection<T: Send + Sync>(&self, name: &str) -> Collection<T> {
        self.db.collection::<T>(name)
    }
}
