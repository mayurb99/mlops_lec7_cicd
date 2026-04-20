# GitHub Secrets Setup Guide
## Lecture 8 — CI/CD Demo
## Do this ONCE before pushing to trigger the pipeline

---

## What Are GitHub Secrets?

GitHub Secrets are encrypted variables stored in your repository settings.
They are NEVER shown in workflow logs — GitHub automatically masks them with ***.
They are the correct way to store AWS credentials, API keys, and tokens.

NEVER put credentials in your workflow YAML file directly.
NEVER commit a .env file with credentials to GitHub.

---

## The 3 Secrets You Need

| Secret Name | Where to get it | Example value |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | AWS Console → IAM → Your User → Security credentials | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | Same page — create access key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | The region your ECR repo is in | `us-east-1` |

---

## Step-by-Step: Create AWS Access Keys

### 1. Open AWS Console → IAM

- Go to: https://console.aws.amazon.com/iam
- Click **Users** in the left sidebar
- Click your username (or create a new one for CI/CD)

### 2. Go to Security credentials tab

- Click the **Security credentials** tab
- Scroll down to **Access keys**
- Click **Create access key**

### 3. Choose use case

- Select **"Command Line Interface (CLI)"**
- Check the confirmation box
- Click **Next**

### 4. Add a description tag

- Description: `GitHub Actions CI/CD for churn-api`
- Click **Create access key**

### 5. COPY BOTH VALUES NOW

```
Access key ID:        AKIAIOSFODNN7EXAMPLE
Secret access key:    wJalrXUtnFEMI/K7MDENG/...
```

**WARNING: The secret access key is shown ONLY ONCE. Copy it now.**
If you close this page without copying, you must create a new key.

---

## Step-by-Step: Add Secrets to GitHub

### 1. Open your GitHub repository

Go to: `https://github.com/YOUR_USERNAME/YOUR_REPO`

### 2. Navigate to Settings → Secrets

```
Your Repo
  └── Settings (top tab)
        └── Secrets and variables (left sidebar)
              └── Actions
                    └── Repository secrets
```

### 3. Add each secret

Click **"New repository secret"** for each:

**Secret 1:**
- Name: `AWS_ACCESS_KEY_ID`
- Secret: paste your Access Key ID
- Click **Add secret**

**Secret 2:**
- Name: `AWS_SECRET_ACCESS_KEY`
- Secret: paste your Secret Access Key
- Click **Add secret**

**Secret 3:**
- Name: `AWS_REGION`
- Secret: `us-east-1` (or your region)
- Click **Add secret**

### 4. Verify all three appear

You should see:
```
Repository secrets
  AWS_ACCESS_KEY_ID        Updated just now
  AWS_SECRET_ACCESS_KEY    Updated just now
  AWS_REGION               Updated just now
```

---

## Minimum IAM Permissions Required

Your AWS user/role needs these permissions for the pipeline to work:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeImages",
        "ecr:CreateRepository"
      ],
      "Resource": "*"
    }
  ]
}
```

In AWS Console → IAM → Your User → Add permissions → Create inline policy → paste the JSON above.

---

## After Setup — Test It

1. Make a small change to `app.py` (e.g., change a comment)
2. `git add . && git commit -m "test ci/cd pipeline"`
3. `git push`
4. Go to: `https://github.com/YOUR_USERNAME/YOUR_REPO/actions`
5. Watch the **ML API CI/CD** workflow run
6. Both jobs should turn green in about 3-4 minutes

If it fails:
- Click the failed job → expand failed step → read the error
- Most common issue: IAM permissions missing for ECR
- Second most common: wrong secret name (must match exactly)
