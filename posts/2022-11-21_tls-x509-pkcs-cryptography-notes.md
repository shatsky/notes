---
title: TLS/X.509/PKCS cryptography notes
summary: Notes about cryptography which I started writing while diving into some crypto stuff at work, grown into detailed explanation
---

## Basics

First items are pretty basic and written down mostly to help explain my non-IT friends what I'm doing (no NDA violations).

*If you want to ask immediately "what exactly of things which I use daily does this article explain", you may jump to HTTPS paragraph as alternate "entry point" and try reading backwards.*

All non-dumb individuals grown with computers around have intuitive basic idea of computer cryptography as something which has "keys" (which are, as everything in computers, numbers represented as bytes), "encryption", which is transformation of original data into something non-readable, and "decryption", which is reverse process. Few less obvious important generic features of modern cryptographic systems:

- encrypted data should have no statistical correlation with original data (to make it impossible for cracker to decrypt it using statistical analysis)
- understanding of crypto algorithm should not be helpful for cracker (to make it possible for everyone to use same crypto software)

*"Perfect" solution to remove correlation would be to combine each symbol of data with symbol of random sequence, effectively turning data into "random noise"; cryptosystem in which "key" is (unique) random sequence with same length as data is truly, absolutely unbreakable, but nightmare to use in practice ("one-time crypto pads" for spies); in practical cryptosystem with good balance between security and useability, keys have fixed length (short, but still long enough to make bruteforcing practically impossible) and random values, and cryptosystem operation can be seen as "stretching" enthropy of the key to the length of the data*

*On the bruteforce resistance of modern cryptosystems: with 256 bit key length, key can have 2\*\*256=115792089237316195423570985008687907853269984665640564039457584007913129639936 different values; with current RAM speeds, it will take (2\*\*256)\*8/30000000000/3600/24/365=9.791314834882142e+59 (10^59) years just to write all possible values to RAM (age of the Universe is theorerized to be 1.37e+10 years)*

*TODO with asymmetric crypto only used for signing in modern applications, it may be better to present it as signing tool, instead of starting with encryption and slowly crawling to signing and auth*

*TODO language unification: crypto system/mechanism/algorithm/method, communication/connection/channel, etc.*

**Symmetric and asymmetric cryptography (aka public key cryptography)**: asymmetric crypto systems have "keypairs", consisting of "public key" used to encrypt data and "private key" used to decrypt (mathematical design of such crypto system should make it impossible to derive private key from public key, i. e. to decrypt data without private key); "symmetric cryptography" is "retrospective" term for non-asymmetric crypto systems which use one key (now often called "symmetric key") for both encryption and decryption. Asymmetric cryptography helps solve two problems, known as key distribution problem and authentication (see below).

Common symmetric crypto systems: AES

Common asymmetric crypto systems: RSA, ECDSA

**Key distribution problem**: in communication system with X users, every of them wanting to be able to communicate with any other (securely and only via the communication system), with symmetric cryptography only, one key has to be generated per every pair of users (X\*(X-1) keys total, which is a lot), and every such key has to be somehow securely shared between one pair of users. With asymmetric cryptography, every user has to generate just one keypair (X keypairs total). Then, any user can use public key of another user to send them encrypted message which only they can decrypt with their private key. However

- asymmetric crypto requires more computing resources, therefore in practice it's only used for secure negotiation of symmetric key, which is then used to encrypt actual data
- even though public key is not secret by design, secure public key delivery requires authentication (see below)
- there's another solution for secure negotiation of symmetric key, called Diffie-Hellman key exchange (see below), but it also requires authentication

**Authentication problem**: authentication is verification that someone is indeed one they pretend to be. For secure communication, it's necessary to be able to verify that message received from other party was indeed sent by that party and was not changed (perhaps maliciously) in process of delivery. Even with invention of mechanisms which allow negotiation of encryption with non secret messages, there's still threat of "man-in-the-middle" attacker communicating with both parties pretending to be another party with each of them, making such systems insecure without means of authentication. Besides encryption, there's another use of asymmetric crypto known as digital signature (see below). It allows to invent certificates and PKI (see below) which solve authentication problem

*TODO what is correct to speak of as being authenticated, party or messages/data supposedly received from that party? Many resources use "authentication of party" concept, but it creates some confusion, as in communication system party never "touches" another party, only received messages*

**Diffie-Hellman key exchange**: algorithm which allows 2 parties to negotiate a common secret number (i. e. symmetric key) in such way that it's not possible to obtain it from intercepted negotiation messages

*All asymmetric crypto and DH algorithms are based on "one-way functions": mathematical functions for which it's "computationally easy" (read: possible almost instantly) to compute function value from argument, but "computationally hard" (read: not possible at all, apart from bruteforcing which should take ages) to calculate original argument from function value. Funnily enough, all such functions used in existing crypto are not mathematically proven to be truly "one-way functions"; there's just public consensus that it's safe enough to use crypto based upon them, because their reversal "intuitively feels" impossible and no one has yet published evidence of existence of working method for it, despite great fame and awards (though not without grain of salt) waiting for anyone who does it; this question is in fact case of fundamental "P?NP" problem famous in maths/CS community*

**Digital signature**: short fixed length data derived from data and private key, which allows anyone with same data and corresponding public key to verify that it was generated by someone who has the private key. Signature itself allows to authenticate data provided that public key is already authenticated, but public key itself has to be authenticated somehow.

*Generation of the signature usually includes preliminary hashing step to transform arbitrary long message into short fixed length data, which is subsequently transformed into signature with use of private key; RSA signing is basically "decryption" of "message representative" (hash of signed data extended with some additional data containing id of the used hash function); RSA standard calls it "application of signing primitive", where "signing primitive" is same as "decryption primitive" and basically means main step of RSA decryption algorithm (one which involves the private key), also there are some pre and post transformations*

*New asymmetric crypto systems standards don't even define encryption/decryption procedures, only signing/verification*

**Certificate (aka public key certificate)**: public key with additional information which is used to identify its owner and to authenticate (i. e. to check whether it really belongs to the party it is supposed to belong to), including

- owner identity/validity boundaries (such as Internet domains, time range; you may already recognize common secure connection errors displayed in browser)
- signature of certificate data produced with private key of trusted authority
- id of this authority (needed to find "higher" certificate with authority public key needed to validate the signature)

With this additional information and availability of "linked" "higher" certificate which is already trusted (not just in sense of containing public key which really belongs to the authority, but also in sense that authority won't sign certificate which couples identity of some party with public key which doesn't belong to it), certificate can be validated, i. e. if its signature is verified successfully, then public key in it can be considered authentic (created by the party and not by "man in the middle" which wants to decrypt intercepted data or forge signatures while pretending to be that party)

*Yes, dependency on another trusted certificate for certificate validation creates a "loop", check next items to see how this "loop" is "broken"*

**Self signed certificate**: certificate which is signed with private key corresponding to public key which it contains; i. e. it doesn't link to "higher" authority certificate

**Root certificate**: self signed certificate that is issued by publicly trusted authority, distributed with programs, device firmwares, etc., which are preconfigured to consider it trusted

**CA (Certification Authority)**: publicly trusted authorities which sign (issue) certificates and provide root certificates to validate signed ones; trust in these is based on publicity of key figures, absense of proven accusations of signing malicious certificates or leaking private keys, and their interest in maintaining their clean reputation (as they make profit from it, either via payments for signing certificates, or somehow else)

*There are means of handling incidents like fraudulent certificate signing or CA private key leak, allowing quick delivery of information about no-longer-to-be-trusted certificates and keys to software, generally known as "certificate revocation"; huge incidents with revocation of globally used root CA certificates happened not many times in Internet history*

**Chain of trust**: chain of certificates in which each next ("higher") one is authority certificate for previous one, so that each previous can be validated via next one, ending with trusted root certificate

**CSR (Certificate Signing Request)**: message in certain defined format, similar to self signed certificate, but intended for CA which should sign the certificate with their private key

*TODO: explain how identity of requesting party is proven/verified by CAs*

**PKI (Public Key Infrastructure)**: infrastructure consisting of all above; one may think about relation of PKI to all above similarly to relation of Internet to network protocols, software and hardware

After certificate received from party is validated, data in messages from it can be authenticated if it's accompanied with digital signature (or is derived from data previously sent to that party encrypted with its public key, or is derived from data received from it which is already authenticated, i. e. whole data is proof that sender has correspondent private key). However, in practice, for same reason for which symmetric crypto is used to encrypt actual data, another authentication mechanism is used for messages encrypted with symmetric crypto, which uses same symmetric key (which has been negotiated with asymmetric crypto and is still proof that sender has private key), generally known as "authenticated encryption"

**X.509**: ITU-T (International Telecommunications Union) standard for PKI, which defines, among other things, format for certificates; there are no really competing standards, so PKI usually means X.509 PKI

*Yes, this means that Internet security is mostly based on trust in CAs*

*Actually, there is at least one notable decentralized "Web of trust" alternative PKI, which doesn't require CAs but requires some effort from common users, somewhat popular in Free software community*

*Also, there are notable "national" PKIs, used within government digital services, e. g. for user auth in government web services which allow to execute actions like property ownership transfer or elections voting; Ukrainian "qualified electronic signature" for example, which is based on some homegrown crypto algorithms with weird decisions, craziest thing probably being that most government web services using it require to upload users private key for auth*

*Some resources claim that PKI \_is\_ X.509 PKI and not applicable as name for other systems which solve same problems with asymmetric crypto, or that PKI is only applicable for centralized systems which have CAs, but that doesn't seem commonly accepted*

**Server and client certificates**: server certificate is certificate intended to be sent by server to clients during encrypted connection establishment; client can validate it via chain of trust and use public key from it to encrypt data sent to server or to authenticate signed data received from server. Client certificate is, well, similar thing but with parties swapped. This distinction is not about certificates themselves, but about how they're being used. Server certificates/certificate-based auth are used everywhere, client ones are rare unless client is software operating without human interaction (e. g. IoT) or, more generally, not managed by user (managing keys and certificates requires knowledge and effort, so when clients are user software with common people using it, it's common practice, once encrypted channel is established with authenticated server and non-authenticated client, for server to ask client for some secret which is easier to manage for person but requires manual input, e. g. password; besides, in many cases server is just "source of public information" and there's no need to care about who is client)

*Client certificates/certificate-based auth in user software are predominantly used for securing access to things which are high value targets for hackers, such as administrative interfaces of important services*

**TLS (Transport Layer Security) and SSL (Secure Socket Layer)**: common network protocols for establishing secure encrypted channel over TCP/IP (Internet), which rely on X.509 PKI for most usecases; TLS is modern one, standardized by IETF, and SSL is its long-deprecated predecessor, its name still occurring here and there, sometimes as synonym. Process of establishing TLS connection is called "handshake". Handshake includes symmetric key negotiation and authentication (via certificate). For TLS 1.3, list of supported asymmetric crypto systems for symmetric key negotiation signing can be seen in https://datatracker.ietf.org/doc/html/rfc8446#section-4.2.3 ; list of supported symmetric crypto systems for encrypting data can bee seen in https://datatracker.ietf.org/doc/html/rfc8446#appendix-B.4

https://www.cloudflare.com/learning/ssl/what-happens-in-a-tls-handshake/

*Many resources claim that "TLS 1.3 doesn't support RSA anymore", but this really means "RSA key exchange algorithm", i. e. variant when security of symmetric key negotiation is solely based on RSA and requires key negotiation messages to be encrypted with RSA; in TLS 1.3 there's only DH key exchange with certificate-based auth (signing DH key exchange for other party to verify with public key in provided certificate), and RSA is still supported for that and is still popular choice when creating certificates*

**HTTPS (HTTP Secure)**: HTTP over TLS, meaning HTTP messages are sent through TLS channel

*At this point you hopefully have generic understanding of what happens when you enter "https://..." URL in browser and see familiar "green lock" icon upon page loading... Or secure connection error*

**OpenSSL**: common open source cryptographic software library providing implementations of common crypto systems, formats and protocols, including X.509 PKI and TLS, used by most web servers in the Internet; also includes utilities to generate and manage asymmetric crypto keypairs, certificates, etc.

*There are other common TLS implementations, including GnuTLS and NSS (used by Firefox)*

**Let's summarize:**

1. **Asymmetric crypto allows, having authentic public key of other communicating party which possesses matching private key, to authenticate messages with cryptographic signatures received from that party (authentication of messages via public keys)**
2. **PKI (system of certificates) allows communicating party to verify that provided public key is authentic (authentication of public keys via certificates). Software/hadware relying on X.509 PKI has relatively small number of preinstalled trusted root certificates containing public keys of "certificate authorities" which are "under the watchful eye of the tech community"; all other public keys which should be authenticated are distributed in certificates which are signed by CAs and validated via root certificates**
3. **Algorithms-protocols of secure generation of secret key (Diffie-Hellman) allow communicating parties, with authentication provided by asymmetric cryptography and PKI, to securily generate shared encryption key, which can't be obtained from intercepted messages**
4. **Secure communication systems are designed to transform data in such way that every bit of sent data becomes encrypted proof that sending party has private key which matches public key; without having the private key it's impossible to send anything which won't be rejected**

## Storing crypto keys and other objects

Crypto keys and other objects have to be serialized and encoded to be stored in files and passed over networks

**ASN.1 (Abstract Syntax Notation One)**: language for describing data structures intended for serializing data of crypto objects such as keys (key components), with possible nesting. Crypto standards typically define ASN.1 object types (strings like RSAPublicKey with following ASN.1 code)

**BER/DER (Basic/Distinguished Encoding Rules)**: binary encoding rules for ASN.1; if ASN.1 is like Unicode, BER/DER are like UTF8. Difference between BER and DER is that BER may allow an ASN.1 object to be serialized to byte sequence in multiple ways, producing different byte sequences, while DER is subset (or superset) of BER which further restricts encoding rules so that unique ASN.1 object is always serialized to unique byte sequence (e. g. important for crypto signatures)

**PEM (Privacy-Enhanced Mail)**: text format for encoding BER/DER-encoded ASN.1 object as string of printable characters, contains base64 string which encodes BER/DER binary data, prepended and appended with human-readable header footer lines `-----BEGIN <label>-----` `-----END <label>-----`, where `<label>` indicates ASN.1 object type, e. g. `RSA PUBLIC KEY` for RSAPublicKey; keys and other crypto objects are usually stored in PEM files (but sometimes in raw BER/DER binary data files); the following table contains PEM labels known to OpenSSL

| PEM label               | ASN.1 object type       | defined in    | notes                                                                                                 |
| ----------------------- | ----------------------- | ------------- | ----------------------------------------------------------------------------------------------------- |
| ANY PRIVATE KEY         |                         |               |                                                                                                       |
| CERTIFICATE             | Certificate             | X.509 rfc5280 | contains certificate data incl. public key as nested subjectPublicKeyInfo                             |
| CERTIFICATE REQUEST     |                         |               |                                                                                                       |
| CMS                     |                         |               |                                                                                                       |
| DH PARAMETERS           |                         |               |                                                                                                       |
| DSA PARAMETERS          |                         |               |                                                                                                       |
| DSA PUBLIC KEY          |                         |               |                                                                                                       |
| EC PARAMETERS           |                         |               |                                                                                                       |
| EC PRIVATE KEY          |                         |               |                                                                                                       |
| ECDSA PUBLIC KEY        |                         |               |                                                                                                       |
| ENCRYPTED PRIVATE KEY   | EncryptedPrivateKeyInfo | PKCS8 rfc5208 | contains encryption info and nested encrypted PrivateKeyInfo                                          |
| PARAMETERS              |                         |               |                                                                                                       |
| PKCS #7 SIGNED DATA     |                         |               |                                                                                                       |
| PKCS7                   |                         |               |                                                                                                       |
| PRIVATE KEY             | PrivateKeyInfo          | PKCS8 rfc5208 | similar to subjectPublicKeyInfo                                                                       |
| PUBLIC KEY              | subjectPublicKeyInfo    | X.509 rfc5280 | contains info about type of key and nested ASN.1 obj of appropriate type (e. g. RSAPublicKey for RSA) |
| RSA PRIVATE KEY         | RSAPrivateKey           | PKCS1 rfc3447 | contains all (private and public) RSA key components                                                  |
| SSL SESSION PARAMETERS  |                         |               |                                                                                                       |
| TRUSTED CERTIFICATE     |                         |               |                                                                                                       |
| X509 CRL                |                         |               |                                                                                                       |
| X9.42 DH PARAMETERS     |                         |               |                                                                                                       |
| DSA PRIVATE KEY         |                         |               |                                                                                                       |
| NEW CERTIFICATE REQUEST |                         |               |                                                                                                       |
| RSA PUBLIC KEY          | RSAPublicKey            | PKCS1 rfc3447 | contains RSA public key components                                                                    |
| X509 CERTIFICATE        | Certificate             | X.509 rfc5280 | same as CERTIFICATE                                                                                   |

**PKCS (Public Key Cryptography Standards)**: set of, as the name suggests, public key cryptography (asymmetric cryptography) standards, which are referred as "PKCS #`<number of the standard>`"

**PKCS1 RSA key formats aka RSAPublicKey/RSAPrivateKey**: ASN.1 structures for RSA key data; defined in PKCS1 standard as RSAPublicKey/RSAPrivateKey ASN.1 types which are sequences of key components; defined in PKCS1 standard

**PKCS8 generic key formats aka X.509 aka subjectPublicKeyInfo/EncryptedPrivateKeyInfo**: ASN.1 structures for different keys of different types which holds them together with information about their type; defined in PKCS8(?) standards as subjectPublicKeyInfo type, which is sequence of AlgorithmIdentifier type obj and bit string holding BER(?)-encoded ASN.1 structure correspondent to the key type, e. g. RSAPublicKey for RSA

**X.509 cert format**: subjectPublicKeyInfo is usually used not standalone but embedded in ASN.1 Certificate type, also defined in X.509, which holds all information about certificate

## HSMs and PKCS11

Generic purpose computers and software are too complex and have too many vulnerabilities to trust them secret keys

**HSM (hardware security module)**: hardware which can store cryptographic objects "non-extractable" and perform crypto operations with them; so that it's like a black box; primarily used to protect private keys, so that even if host computer is compromised, they cannot be stolen

**PKCS11**: industrial standard API for accessing HSMs, includes functions for importing, generating keys, encrypting/decrypting, signing/verifying data; supported by various applications and libraries, incl. OpenSSL (via p11 engine)

**PKCS11 mechanisms**: entities which represent crypto algorithms; also API constants which are accepted by relevant PKCS11 functions as args to indicate which crypto algorithm to use for operation; e. g.

- 0x0 CKM_RSA_PKCS_KEY_PAIR_GEN (implements RSA keypair creation, accepted by PKCS11 function C_GenerateKeyPair())
- 0x1 CKM_RSA_PKCS (implements PKCS1 RSA encryption and signature schemes with padding, accepted by relevant PKCS11 functions like C_Sign())

**PKCS11 objects**: entities which represent crypto objects such as keys; PKCS11 doesn't define how storage of objects is implemented, only how to query them and their attributes

**PKCS11 attributes**: "key/id-value" pairs which PKCS11 object "consists of" "from client perspective", incl. its type and type-specific attributes such as key components; queried/updated via C_GetAttributeValue()/C_SetAttributeValue() functions, which take struct holding numeric "key/id" of the attribute, possible "key/id"s defined as `CKA_<...>` in PKCS11 headers (of course attempt to query secret key component value with proper PKCS11 implementation will return err code)

**PKCS11 URI**: string to identify object in HSM; it's just standardized text serialized format for providing data such as token and object labels in configuration/cmdline args of software which uses PKCS11, which should parse it and perform PKCS11 find op using this data to get handle(s) of matching object(s)

## Specific crypto systems

**RSA Digest**: PKCS1 RSA standard defines one of intermediate forms of data in signing procedure as "DigestInfo"; it's DER-encoded ASN.1 DigestInfo type obj consisting of hash function id and plaintext hash; it is expected as input in PKCS11 C_Sign() with mechanism CKM_RSA_PKCS 

**RSA schemes, padding and primitives**: "raw RSA" is described as `mod(pow(data, exponent), modulus)`; size of data is assumed to be equal to key size, and to be able to process variable length data (between 0 and key size) it's required to have defined steps to embed and use information about where "actual data" begins in data; therefore RSA standards describe "schemes" which include steps adding padding data and stripping this padding on reverse transformation; simplest one is basically all-0xff fill ending with 0x00 byte denoting end of padding, but this has some security problem, so there are more complicated ones with similar idea; steps which are actual "raw RSA" are called "encryption/decryption/signing/verification primitives" (and are identical in all schemes, only difference is that private exponent is used for signing and decryption, public exponent is used for encryption and verification); in PKCS11, standardized RSA schemes are represented with different CKM_RSA_* mechanisms, plus CKM_RSA_X_509 for "raw RSA" (which is supposed to be used by software to implement secure scheme in such way that it handles padding in its own code, using PKCS11 only to store keys securily)

**AES initialization vector and block chaining**: as any modern cipher, AES turns any data info something which looks like noise; however, as it operates key-sized blocks of data, in case current block data being the only variable input, same blocks will produce same encrypted blocks, possibly giving some hint about what's being encrypted (e. g. image bitmaps can be recognizable); to avoid this, AES has another input in addition to data and key, called "initialization vector". In block chaining mode, encrypted block is used as iv for next block encryption, making encrypted data look like noise even on block level (picking IV value for 1st block is still a thing)

## Tools

Binary<>ascii hex conversions

- hex to bin: `echo $ascii_hex_string|xxd -r -p` (all chars which are not hex digits are ignored)
- bin to hex: `|xxd -p` ("plain hexdump")
- bin to hex: `|xxd -i` (C array, if filename given to xxd it will add array declaration and length variable)

- PEM string to bin: `|base64 -d`
- bin to PEM string: `|base64`

- parse ASN.1 data (PEM): `openssl asn1parse -in $filename`
- parse ASN.1 data (binary): `openssl asn1parse -inform DER -in $filename`

*TODO add commands for conversions between key&cert formats, inspecting contents, creating keypairs and certs, test TLS server*
