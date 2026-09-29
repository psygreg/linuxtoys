use pyo3::prelude::*;
use pyo3::types::PyDict;
use prost::Message;
use sha2::{Digest, Sha256};
use std::fs;
use tonic::codegen::http::uri::PathAndQuery;
use tonic::metadata::MetadataValue;
use tonic::transport::{Channel, ClientTlsConfig, Endpoint};
use tonic::{Request, Status};

const RATINGS_ENDPOINT: &str = "https://ratings.ubuntu.com";

#[derive(Clone, PartialEq, Message)]
struct AuthenticateRequest { #[prost(string, tag="1")] id: String }
#[derive(Clone, PartialEq, Message)]
struct AuthenticateResponse { #[prost(string, tag="1")] token: String }
#[derive(Clone, PartialEq, Message)]
struct GetBulkRatingsRequest { #[prost(string, repeated, tag="1")] snap_ids: Vec<String> }
#[derive(Clone, PartialEq, Message)]
struct GetBulkRatingsResponse { #[prost(message, repeated, tag="1")] ratings: Vec<ChartData> }
#[derive(Clone, PartialEq, Message)]
struct ChartData { #[prost(float, tag="1")] raw_rating: f32, #[prost(message, optional, tag="2")] rating: Option<Rating> }
#[derive(Clone, PartialEq, Message)]
struct Rating {
    #[prost(string, tag="1")] snap_id: String,
    #[prost(uint64, tag="2")] total_votes: u64,
    #[prost(enumeration="RatingsBand", tag="3")] ratings_band: i32,
    #[prost(string, tag="4")] snap_name: String,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, prost::Enumeration)]
#[repr(i32)]
enum RatingsBand { VeryGood=0, Good=1, Neutral=2, Poor=3, VeryPoor=4, InsufficientVotes=5 }
#[derive(Clone, PartialEq, Message)]
struct GetSnapVotesRequest { #[prost(string, tag="1")] snap_id: String }
#[derive(Clone, PartialEq, Message)]
struct GetSnapVotesResponse { #[prost(message, repeated, tag="1")] votes: Vec<Vote> }
#[derive(Clone, PartialEq, Message)]
struct Vote {
    #[prost(string, tag="1")] snap_id: String,
    #[prost(int32, tag="2")] snap_revision: i32,
    #[prost(bool, tag="3")] vote_up: bool,
    #[prost(message, optional, tag="4")] timestamp: Option<prost_types::Timestamp>,
    #[prost(string, tag="5")] snap_name: String,
}
#[derive(Clone, PartialEq, Message)]
struct VoteRequest { #[prost(string, tag="1")] snap_id: String, #[prost(int32, tag="2")] snap_revision: i32, #[prost(bool, tag="3")] vote_up: bool }
#[derive(Clone, PartialEq, Message)]
struct Empty {}

fn identity() -> Result<String, String> {
    let user = std::env::var("USER").or_else(|_| std::env::var("LOGNAME")).unwrap_or_else(|_| "unknown".into());
    let machine = ["/etc/machine-id", "/var/lib/dbus/machine-id"].iter()
        .find_map(|p| fs::read_to_string(p).ok().map(|v| v.trim().to_string()).filter(|v| !v.is_empty()))
        .ok_or_else(|| "machine id unavailable".to_string())?;
    let digest = Sha256::digest(format!("{}:{}", user, machine).as_bytes());
    Ok(format!("{:x}", digest))
}

async fn channel() -> Result<Channel, String> {
    Endpoint::from_static(RATINGS_ENDPOINT)
        .tls_config(ClientTlsConfig::new().domain_name("ratings.ubuntu.com")).map_err(|e| e.to_string())?
        .connect().await.map_err(|e| e.to_string())
}

async fn unary<Req, Resp>(channel: Channel, path: &'static str, message: Req, token: Option<&str>) -> Result<Resp, String>
where Req: Message + Default + Send + Sync + 'static, Resp: Message + Default + Send + Sync + 'static {
    let mut grpc = tonic::client::Grpc::new(channel);
    grpc.ready().await.map_err(|e| e.to_string())?;
    let mut request = Request::new(message);
    if let Some(token) = token {
        let value: MetadataValue<_> = format!("Bearer {}", token).parse().map_err(|e| format!("invalid auth token: {e}"))?;
        request.metadata_mut().insert("authorization", value);
    }
    grpc.unary(request, PathAndQuery::from_static(path), tonic::codec::ProstCodec::default())
        .await.map(|r| r.into_inner()).map_err(|e: Status| e.to_string())
}

async fn authenticate(ch: Channel) -> Result<String, String> {
    let response: AuthenticateResponse = unary(ch, "/ratings.features.user.User/Authenticate", AuthenticateRequest { id: identity()? }, None).await?;
    if response.token.is_empty() { Err("Canonical ratings returned an empty token".into()) } else { Ok(response.token) }
}

fn runtime() -> Result<tokio::runtime::Runtime, String> {
    tokio::runtime::Builder::new_current_thread().enable_all().build().map_err(|e| e.to_string())
}

#[pyfunction]
pub(crate) fn snap_bulk_ratings(py: Python<'_>, snap_ids: Vec<String>) -> PyResult<Py<PyAny>> {
    let ids: Vec<String> = snap_ids.into_iter().map(|v| v.trim().to_string()).filter(|v| !v.is_empty()).collect();
    let result = py.allow_threads(move || -> Result<Vec<(String,String,u64,f32,i32)>, String> {
        if ids.is_empty() { return Ok(Vec::new()); }
        runtime()?.block_on(async move {
            let ch = channel().await?; let token = authenticate(ch.clone()).await?;
            let response: GetBulkRatingsResponse = unary(ch, "/ratings.features.app.App/GetBulkRatings", GetBulkRatingsRequest { snap_ids: ids }, Some(&token)).await?;
            Ok(response.ratings.into_iter().filter_map(|v| v.rating.map(|r| (r.snap_id,r.snap_name,r.total_votes,v.raw_rating,r.ratings_band))).collect())
        })
    });
    let out = PyDict::new(py);
    match result {
        Ok(rows) => for (id,name,count,raw,band) in rows {
            let item=PyDict::new(py); item.set_item("snap_name",name)?; item.set_item("total_votes",count)?; item.set_item("raw_rating",raw)?; item.set_item("ratings_band",band)?; out.set_item(id,item)?;
        },
        Err(error) => { out.set_item("_error", error)?; }
    }
    Ok(out.unbind().into_any())
}

#[pyfunction]
pub(crate) fn snap_user_vote(py: Python<'_>, snap_id: String) -> PyResult<Py<PyAny>> {
    let id=snap_id.trim().to_string();
    let out=PyDict::new(py);
    if id.is_empty(){ return Ok(out.unbind().into_any()); }
    let result=py.allow_threads(move || -> Result<Option<(bool,i32)>,String>{ runtime()?.block_on(async move{
        let ch=channel().await?; let token=authenticate(ch.clone()).await?;
        let response:GetSnapVotesResponse=unary(ch,"/ratings.features.user.User/GetSnapVotes",GetSnapVotesRequest{snap_id:id},Some(&token)).await?;
        Ok(response.votes.into_iter().max_by_key(|v|v.timestamp.as_ref().map(|t|t.seconds).unwrap_or(0)).map(|v|(v.vote_up,v.snap_revision)))
    })});
    match result {
        Ok(Some((vote,revision))) => { out.set_item("vote_up",vote)?; out.set_item("revision",revision)?; },
        Ok(None) => {},
        Err(error) => { out.set_item("_error",error)?; }
    }
    Ok(out.unbind().into_any())
}

#[pyfunction]
pub(crate) fn submit_snap_vote(py: Python<'_>, snap_id:String, snap_revision:i32, vote_up:bool) -> PyResult<()> {
    let id=snap_id.trim().to_string(); if id.is_empty()||snap_revision<=0{return Err(pyo3::exceptions::PyValueError::new_err("invalid snap vote data"))}
    py.allow_threads(move || -> Result<(),String>{ runtime()?.block_on(async move{
        let ch=channel().await?; let token=authenticate(ch.clone()).await?;
        let _:Empty=unary(ch,"/ratings.features.user.User/Vote",VoteRequest{snap_id:id,snap_revision,vote_up},Some(&token)).await?; Ok(())
    })}).map_err(pyo3::exceptions::PyRuntimeError::new_err)
}
