"""
database/seed_policies.py — Rich in-code policy corpus → ChromaDB with BGE-small embeddings
"""
from pathlib import Path
import textwrap

CHROMA_PATH = Path(__file__).resolve().parent.parent / "enterprise_chroma_db"

# ---------------------------------------------------------------------------
# Policy corpus — 15 sections, 3-5 sentences each
# ---------------------------------------------------------------------------
POLICIES = {
    "Refund Policy": """
        Our standard refund policy allows customers to request a full refund within 30 days of purchase.
        Refunds are processed within 5-7 business days to the original payment method.
        Digital products and downloadable content are eligible for refunds only within 7 days of purchase if the product has not been accessed or downloaded.
        Partial refunds may be granted for subscription services that have been partially used within the billing period.
        To initiate a refund, customers must contact our support team at refunds@company.com with their order number and reason for the refund request.
    """,
    "Returns and Exchanges": """
        Physical products may be returned within 30 days of delivery in their original, unopened condition.
        Items that have been opened, used, or damaged by the customer are not eligible for a full refund but may qualify for an exchange.
        Return shipping costs are the responsibility of the customer unless the return is due to a defective or incorrect item.
        Exchanges can be processed for items of equal or lesser value; if the new item costs more, the customer must pay the difference.
        To start a return, visit our Returns Portal at company.com/returns and follow the step-by-step instructions.
    """,
    "Shipping Policy": """
        Standard shipping takes 5-7 business days for domestic orders and 10-14 business days for international orders.
        Expedited shipping (2-3 business days) and overnight shipping options are available at checkout for an additional fee.
        Orders over $75 qualify for free standard shipping within the continental United States.
        International orders may be subject to customs duties, import taxes, and brokerage fees, which are the responsibility of the recipient.
        Once an order ships, customers receive a confirmation email with a tracking number to monitor delivery progress.
    """,
    "Billing and Payment": """
        We accept all major credit cards (Visa, MasterCard, American Express, Discover), PayPal, and bank transfers.
        Subscription billing occurs automatically on the same date each month or year, depending on the plan selected at signup.
        Invoices are emailed to the registered billing address within 24 hours of each successful payment.
        If a payment fails, we will retry the charge up to three times over five days before suspending the account.
        Customers can update their billing information at any time in their Account Settings under the Billing tab.
    """,
    "Account Security": """
        All customer accounts are protected with industry-standard AES-256 encryption for stored data.
        We enforce multi-factor authentication (MFA) for all accounts with administrative privileges.
        Customers are advised to use a unique, strong password of at least 12 characters combining letters, numbers, and symbols.
        Suspicious activity such as multiple failed login attempts will trigger an automatic account lock and email notification.
        Our security team conducts quarterly penetration tests and annual third-party security audits to maintain platform integrity.
    """,
    "Password Reset Procedure": """
        To reset your password, click the 'Forgot Password' link on the login page and enter your registered email address.
        A secure reset link will be sent to your email within 2 minutes; the link expires after 15 minutes for security reasons.
        If you do not receive the reset email, check your spam folder or contact support@company.com for assistance.
        After resetting your password, all active sessions on other devices will be automatically logged out.
        For accounts with MFA enabled, you must also verify your identity through the authenticator app after setting a new password.
    """,
    "Data Privacy": """
        We collect only the minimum necessary personal data required to provide our services, in compliance with GDPR and CCPA.
        Customer data is never sold to third parties; it may be shared with service providers only under strict data processing agreements.
        You have the right to access, correct, or delete your personal data at any time by submitting a request to privacy@company.com.
        Data retention periods vary by data type: account data is retained for 3 years post-cancellation; transaction records for 7 years for tax compliance.
        Our full Privacy Policy is available at company.com/privacy and is updated whenever there are material changes to our data practices.
    """,
    "SLA Commitments": """
        Critical priority tickets (system outages, security incidents) receive a first response within 1 hour and resolution within 4 hours.
        High priority tickets receive a first response within 4 hours and a target resolution time of 24 hours.
        Medium priority tickets receive a first response within 8 business hours with a resolution target of 72 hours.
        Low priority tickets receive a first response within 2 business days with no guaranteed resolution time, though we aim to resolve within 1 week.
        SLA commitments apply during standard business hours (Monday to Friday, 9AM to 6PM EST); 24/7 support is available on Enterprise plans.
    """,
    "Escalation Procedure": """
        If a ticket remains unresolved beyond its SLA target, it is automatically escalated to a senior support engineer.
        Customers can manually escalate a ticket by replying with the word 'ESCALATE' in the ticket thread or by calling the priority support line.
        Escalated tickets are flagged with 'Critical' priority and assigned to the Team Lead of the relevant department.
        The customer will receive a personalized update call or email within 2 hours of escalation.
        Repeated escalations on the same account are reviewed monthly by Customer Success Management to identify systemic issues.
    """,
    "Technical Support Process": """
        Technical support is available via live chat, email, and phone during business hours for Standard plan customers.
        Enterprise customers have access to a dedicated Technical Account Manager (TAM) for proactive support and quarterly reviews.
        When submitting a technical issue, please include your account ID, a description of the problem, steps to reproduce, and any error messages.
        Our support team may request remote access to your environment to diagnose complex issues; this requires explicit customer consent.
        Known issues and service status are published in real time at status.company.com; customers can subscribe to incident notifications.
    """,
    "Subscription Management": """
        Customers can upgrade, downgrade, or cancel their subscription at any time from the Account Settings page.
        Plan upgrades take effect immediately and are prorated for the remainder of the current billing cycle.
        Plan downgrades take effect at the start of the next billing cycle; features of the higher plan remain accessible until then.
        Subscriptions auto-renew at the end of each billing period unless cancelled before the renewal date.
        Customers receive a renewal reminder email 7 days before each annual subscription renewal.
    """,
    "Cancellation Policy": """
        You may cancel your subscription at any time without penalty by navigating to Account Settings > Subscription > Cancel.
        Upon cancellation, your account remains active until the end of the current paid period; no partial refunds are issued for unused time.
        Within 24 hours of cancellation, you will receive an email confirming cancellation and instructions to export your data.
        Reactivating a cancelled account within 90 days restores all previous data and settings.
        After 90 days, cancelled accounts and their data are permanently deleted in accordance with our data retention policy.
    """,
    "Dispute Resolution": """
        In the event of a billing dispute, customers must contact billing@company.com within 30 days of the disputed charge.
        Our billing team will investigate and respond within 5 business days with a resolution or a request for additional information.
        If a chargeback is filed with the payment provider before contacting us, we reserve the right to suspend the account pending investigation.
        Unresolved disputes may be escalated to our Customer Advocacy team, who have authority to offer credits or exceptions.
        We are committed to resolving all disputes fairly and in accordance with applicable consumer protection laws.
    """,
    "Warranty and Guarantees": """
        Physical hardware products are covered by a 1-year limited warranty against manufacturing defects.
        Software products include a 90-day guarantee covering critical bugs that prevent core functionality from working as described.
        Warranty claims must be submitted with proof of purchase and a description of the defect to warranty@company.com.
        Damage caused by misuse, unauthorized modifications, or accidents is not covered under warranty.
        We offer an extended warranty program for hardware products that extends coverage to 3 years for an additional fee.
    """,
    "Contact and Support Channels": """
        General support is available via email at support@company.com with a typical response time of 4-8 business hours.
        Live chat support is available on our website during business hours (Monday to Friday, 9AM to 6PM EST).
        Phone support is available for High and Critical tier customers at 1-800-555-0100; Enterprise customers have a dedicated direct line.
        Our self-service Help Center at help.company.com contains over 500 articles, tutorials, and FAQs.
        Community forums at community.company.com allow customers to share tips, report issues, and get peer support 24/7.
    """,
}


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 40) -> list[str]:
    """Split text into overlapping chunks of approximately chunk_size characters."""
    text = " ".join(text.split())  # normalize whitespace
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to break at a sentence boundary
        if end < len(text):
            for punct in (". ", "! ", "? "):
                idx = text.rfind(punct, start, end)
                if idx != -1:
                    end = idx + 2
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break
    return chunks


def seed_chromadb():
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_core.documents import Document

    print("🔄 Loading BGE-small embedding model (may take a moment on first run)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    all_docs = []
    for section, text in POLICIES.items():
        chunks = chunk_text(text, chunk_size=220, overlap=50)
        for i, chunk in enumerate(chunks):
            all_docs.append(Document(
                page_content=chunk,
                metadata={"section": section, "chunk_index": i},
            ))

    print(f"📄 Total policy chunks: {len(all_docs)}")

    # Clear existing collection and re-seed
    vectorstore = Chroma(
        collection_name="enterprise_policies",
        embedding_function=embeddings,
        persist_directory=str(CHROMA_PATH),
    )

    # Delete existing documents if any
    try:
        existing = vectorstore.get()
        if existing and existing.get("ids"):
            vectorstore.delete(ids=existing["ids"])
            print(f"   Cleared {len(existing['ids'])} existing documents.")
    except Exception:
        pass

    # Add in batches of 50
    batch_size = 50
    for i in range(0, len(all_docs), batch_size):
        batch = all_docs[i:i + batch_size]
        vectorstore.add_documents(batch)
        print(f"   Ingested batch {i // batch_size + 1} ({len(batch)} chunks)")

    final_count = vectorstore.get()
    print(f"✅ ChromaDB seeded at {CHROMA_PATH}")
    print(f"   Total documents in collection: {len(final_count.get('ids', []))}")


if __name__ == "__main__":
    seed_chromadb()
