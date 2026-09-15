# Voluntary email submission

Read this only after the finished model's creator chooses to submit it. The creator uploads a ZIP to WeTransfer or another transfer service and emails its download link for manual review. Submission does not guarantee acceptance or immediate publication.

## Prepare the submission

Reuse information already provided. Collect only missing details:

- The public credit name or pseudonym, or an explicit choice of anonymous credit. Do not request a legal name, postal address or phone number. Keep the sender's email private.
- The intended community website, its operator and submission email, from a verified project source or the creator. None is configured in this release: never invent them. If missing, give a clearly unfinished copyable template rather than an addressed, ready-to-send draft.
- The transfer download link after upload, plus expiry or password only if applicable. Do not request transfer-account credentials.

Explain the permission briefly in the creator's language: the named operator may host and display this submission on the named community website, offer its files for download, make technical formatting changes, and let visitors use them for personal, non-commercial building. The creator retains their rights and chooses their credit. Show the exact English wording for review; never treat the initial wish to submit as acceptance of undisclosed terms or assert an unconfirmed rights declaration on their behalf.

The email permission is separate from the skill's software license and from any public reuse license on the model. Do not automatically select MIT or Creative Commons for the output. `UNLICENSED` may remain when the creator grants only the specific email permission below; it means no general public reuse license was selected. Any existing third-party restrictions still apply. If attribution or a chosen public license needs changing, update the source and regenerate a separate bundle before packing; do not hand-edit hashed exports. `refresh-guide --text-model` cannot change attribution or licensing.

Run `python scripts/brick.py pack OUTPUT --zip PATH.zip` outside repositories. It verifies inventory and hashes without publishing. Use its returned ZIP filename and SHA-256 in the email to identify the exact submission. Keep the email outside the bundle: extra files would invalidate the output contract. Ask the creator to upload that ZIP and provide the link; do not claim upload success without evidence.

## English email template

Replace square-bracket fields with confirmed information. Omit the expiry/password line if unnecessary. The rights paragraph must be reviewed by the creator; if they cannot grant the stated rights, resolve or remove the affected material rather than asserting consent anyway.

```text
To: [verified submission email]
Subject: Community model submission — [model title]

Hello,

Please consider my model for publication on [community website URL].

Model: [model title and model ID]
Credit: [public name/pseudonym, or Anonymous]
Download link: [transfer URL]
ZIP filename: [filename.zip]
ZIP SHA-256: [hash returned by the pack command]
Link expiry / download password: [if applicable]

I confirm that I have the rights and permissions needed to submit the files in this ZIP and grant the permissions below. Any third-party material and applicable license or credit requirements are disclosed below.

I grant [operator name] non-exclusive, worldwide, royalty-free permission to store, reproduce and display the submitted model, renders, building instructions and parts list on [community website URL], and to make the submitted files available there for download. This includes resizing images and making technical format changes for presentation while preserving the substance of my work and the credit specified above. I also permit visitors to download and use these files for personal, non-commercial model building. I retain my rights in my contribution. This permission does not authorize other uses, such as resale of my files or use in separate advertising campaigns.

Third-party material, licenses and required credits: [details, or None if confirmed]
Optional public reuse license: [existing/chosen license, or No additional public license granted]

Thank you.
```

This is a concrete permission template, not a warranty of legal clearance. A declaration cannot grant rights the sender does not hold. The website operator must retain the received email alongside the identified ZIP and review third-party disclosures before publishing; this skill does not perform website administration.

## Draft or copyable fallback

When details are available, use an already available mail tool or app to prepare an unsent draft with the recipient, subject and body. Do not install a mail integration or change the user's mail configuration merely to create a draft. Show the finished text for review, including the permission paragraph. Verify draft creation if the tool supports it; an opened compose window is not proof that a draft was saved. If unavailable or unsuccessful, return the subject and body as copyable text in the conversation. Explain in the user's language that they should review the wording and send it from their own email address if they agree.

Do not send automatically. Draft creation, packaging and a user's general wish to submit do not authorize transmission. Never report the model as submitted or published from draft creation alone.

The template explicitly names uses and attribution following the distinctions in [German Copyright Act section 31](https://www.gesetze-im-internet.de/urhg/__31.html) and [section 13](https://www.gesetze-im-internet.de/urhg/__13.html); it is not a general waiver of the creator's rights.
