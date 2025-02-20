#[macro_export]
macro_rules! register_model {
    ($name:expr, $t:ident) => {
        use futures::stream::TryStreamExt;
        use mongodb::bson::{self, to_bson};
        use mongodb::bson::{doc, Bson};
        use mongodb::error::Error;
        use mongodb::options::UpdateModifications;
        use mongodb::results::InsertManyResult;
        use mongodb::results::UpdateResult;
        use mongodb::Collection;
        use serde::de::DeserializeOwned;

        #[allow(dead_code)]
        impl $t
        where
            $t: DeserializeOwned + Sized,
            Self: Serialize,
        {
            pub fn collection_name() -> &'static str {
                $name
            }

            pub fn collection() -> Collection<$t> {
                crate::db::mongo::MongoDB::instance().collection($t::collection_name())
            }

            pub async fn delete(&self) -> eyre::Result<bool> {
                Self::delete_one(doc! {"_id": self.id.clone()}).await
            }

            pub async fn save(&mut self) -> eyre::Result<&Self> {
                let result = Self::collection()
                    .update_one(
                        doc! {"_id": self.id.clone().unwrap().as_str()},
                        doc! {"$set": self.to_bson()},
                    )
                    .upsert(true)
                    .await?;
                if result.upserted_id.is_some() {
                    let id = result.upserted_id.unwrap();
                    self.id = Some(String::from(id.as_str().unwrap()));
                }
                return Ok(self);
            }

            pub async fn find_all(filter: mongodb::bson::Document) -> Result<Vec<$t>, Error> {
                return Self::collection().find(filter).await?.try_collect().await;
            }

            pub async fn distinct_all(key: String, filter: mongodb::bson::Document) -> Option<Vec<Bson>> {
                return Self::collection().distinct(key, filter).await.ok();
            }

            pub async fn find(
                filter: mongodb::bson::Document,
                skip: Option<u64>,
                limit: Option<i64>,
                sort: Option<mongodb::bson::Document>,
            ) -> Result<Vec<$t>, Error> {
                let col = Self::collection();
                let mut query = col.find(filter);
                if let Some(sk) = skip {
                    query = query.skip(sk);
                }
                if let Some(lm) = limit {
                    query = query.limit(lm);
                }
                if let Some(s) = sort {
                    query = query.sort(s);
                }
                query.await?.try_collect().await
            }

            pub async fn find_one(filter: mongodb::bson::Document) -> Result<Option<$t>, Error> {
                Self::collection().find_one(filter).await
            }

            pub async fn find_by_id(id: String) -> Option<$t> {
                Self::collection().find_one(doc! {"_id": id}).await.unwrap()
            }

            pub async fn create(data: &$t) -> eyre::Result<String> {
                let result = Self::collection().insert_one(data).await?;
                let inserted_id = result.inserted_id.as_str();
                Ok(inserted_id.unwrap().to_string())
            }

            pub async fn update_one(
                filter: mongodb::bson::Document,
                update: impl Into<UpdateModifications>,
            ) -> Result<UpdateResult, Error> {
                Self::collection().update_one(filter, update).await
            }

            pub async fn set_fields_by_id(id: String, fields: mongodb::bson::Document) -> Result<UpdateResult, Error> {
                Self::collection()
                    .update_one(doc! {"_id": id}, doc! {"$set": fields})
                    .await
            }

            pub async fn update_many(
                filter: mongodb::bson::Document,
                update: impl Into<UpdateModifications>,
            ) -> Result<UpdateResult, Error> {
                Self::collection().update_many(filter, update).await
            }

            pub async fn delete_one(filter: mongodb::bson::Document) -> eyre::Result<bool> {
                let result = Self::collection().delete_one(filter).await?;
                Ok(result.deleted_count > 0)
            }

            pub async fn delete_many(filter: mongodb::bson::Document) -> eyre::Result<u64> {
                let result = Self::collection().delete_many(filter).await?;
                Ok(result.deleted_count)
            }

            pub async fn insert_many(docs: Vec<$t>) -> Result<InsertManyResult, Error> {
                Self::collection().insert_many(docs).await
            }

            pub fn to_bson(&self) -> bson::Document {
                let bson = to_bson(self).unwrap();
                if let bson::Bson::Document(document) = bson {
                    document
                } else {
                    panic!("Expected BSON document");
                }
            }
        }
    };
}
