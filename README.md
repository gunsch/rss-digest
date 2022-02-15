## RSS "Daily Digest" aggregator thing

Composes RSS feeds into other RSS feeds

Cloned from the Python/Flask/App Engine getting-started repository.

### Local development

```
export GOOGLE_CLOUD_PROJECT=rss-digest
dev_appserver.py \
    --env_var GOOGLE_APPLICATION_CREDENTIALS=$(readlink -f ./service-account-local-development.json) \
    .
```

