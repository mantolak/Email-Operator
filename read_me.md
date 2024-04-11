# Email Kubernetes Operator

Email Kubernetes Operator which manages custom resources for configuring email sending and sending of emails via a transactional email provider like MailerSend. Operator Created with Python language and [kopf](https://kopf.readthedocs.io/en/stable/) library


# System requirements

1. **Docker** - install from Docker [page](https://docs.docker.com/get-docker/).
2. **Kubernetes** - install from Kubernetes [page](https://kubernetes.io/docs/home/), you can use [Minikube](https://minikube.sigs.k8s.io/docs/start/)  for test purpose.
3. **Mailersend** - api token for [Mailersend](https://www.mailersend.com/) account

# Instalation

### Create **Secret** with encoded api token. 
Encode your Mailersend API Token with base64. You can use command
```
echo "your-api-token" | base64
```
Edit `secret_token.yaml` file and add your encoded api token in 
```
data:
	MAILERSEND_API_TOKEN: your-encoded-api-token
```

### Create **Email** and **EmailSenderConfig** Custom Resource Definitions (CRDs)
Run command
```
kubectl create -f EmailCdr.yaml  
```
and 
```
kubectl create -f EmailSenderConfigCdr.yaml
```

### Create **Service Account**
Run command
```
kubectl create serviceaccount email-operator
```
### Create **Cluster Role** and **Cluster Role Binding**
Run command for Cluster Role creation
```
kubectl create clusterrole mailer-controller-cluster-role --verb='*' --resource=emailsenderconfigs,emails,secrets,events
```
When Custer Role is created, we can create Cluster Role Binding with command
```
kubectl create clusterrolebinding mailer-controller-cluster-role-binding --clusterrole=mailer-controller-cluster-role --serviceaccount=default:email-operator
```
### Create Operator Image
Create Docker image named **kubernetes_operator** used for deployment. Run command 
```
docker build -t kubernetes_operator .
```
### Create Kubernetes Deployment
Run command
```
kubectl create -f deployment.yaml
```
Deployment will create 1 pod with running operator. You can check pod status by running command 
```
kubectl get pods
```
Pod `email-operator***` should be in a `Running` state

# Testing
For testing purpose we can create our own EmailConfig and Email or we can use provided examples. 
### Email Sender Config
Use **emailconfig.yaml** file and update your sender email domain. 
```
spec:
	apiToken: "token-secrets"
	provider: "mailersend"
	senderEmail: "sender@<you-mailersend-domain.com>"
```
To create email config run command
```
kubectl create -f emailConfig.yaml
```
You can verify newly created Email config by running command 
```
kubectl describe emailsenderconfigs my-email-sender-config
```
When Email config is created or updated, operator will configure email sending setting for a particular provider.

To create email run command
```
kubectl create -f email.yaml
```
Kubernetes Operator will automatically send email based on Email config from Email **senderConfigRef**, save email delivery status and email ID for each newly created or updated email. Email status can be verify by running command
```
kubectl describe emails test-email
```