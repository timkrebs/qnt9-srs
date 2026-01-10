"use client"

export default function PrivacyContent() {
  const lastUpdated = "January 10, 2026"

  return (
    <main className="flex-1 pt-14">
      {/* Header */}
      <section className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-6 md:px-8 py-16">
          <h1 className="text-4xl font-semibold text-gray-900 mb-4">
            Privacy Policy
          </h1>
          <p className="text-gray-500">
            Last updated: {lastUpdated}
          </p>
        </div>
      </section>

      {/* Content */}
      <section className="max-w-4xl mx-auto px-6 md:px-8 py-12">
        <div className="prose prose-gray max-w-none">

          {/* Preamble */}
          <h2 id="preamble" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Preamble
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            This Privacy Policy is intended to inform you about the types of your personal data (hereinafter also referred to as &quot;data&quot;) that we process, the purposes for which we process it, and the extent of such processing. This Privacy Policy applies to all processing of personal data carried out by us, both in the context of providing our services and, in particular, on our websites, in mobile applications, and within external online presences such as our social media profiles (hereinafter collectively referred to as the &quot;Online Services&quot;).
          </p>
          <p className="text-gray-600 leading-relaxed mb-8">
            The terminology used is gender-neutral.
          </p>

          {/* Table of Contents */}
          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Table of Contents
          </h2>
          <ul className="list-disc pl-6 mb-8 space-y-2 text-gray-600 columns-1 md:columns-2">
            <li><a href="#preamble" className="text-blue-600 hover:underline">Preamble</a></li>
            <li><a href="#controller" className="text-blue-600 hover:underline">Controller</a></li>
            <li><a href="#overview" className="text-blue-600 hover:underline">Overview of Processing Activities</a></li>
            <li><a href="#legal-bases" className="text-blue-600 hover:underline">Applicable Legal Bases</a></li>
            <li><a href="#security" className="text-blue-600 hover:underline">Security Measures</a></li>
            <li><a href="#international-transfers" className="text-blue-600 hover:underline">International Data Transfers</a></li>
            <li><a href="#retention" className="text-blue-600 hover:underline">General Information on Data Retention and Deletion</a></li>
            <li><a href="#rights" className="text-blue-600 hover:underline">Rights of Data Subjects</a></li>
            <li><a href="#hosting" className="text-blue-600 hover:underline">Provision of the Online Services and Web Hosting</a></li>
            <li><a href="#registration" className="text-blue-600 hover:underline">Registration, Login, and User Account</a></li>
            <li><a href="#sso" className="text-blue-600 hover:underline">Single Sign-On Authentication</a></li>
            <li><a href="#contact" className="text-blue-600 hover:underline">Contact and Enquiry Management</a></li>
            <li><a href="#newsletter" className="text-blue-600 hover:underline">Newsletter and Electronic Notifications</a></li>
            <li><a href="#analytics" className="text-blue-600 hover:underline">Web Analytics, Monitoring, and Optimisation</a></li>
            <li><a href="#plugins" className="text-blue-600 hover:underline">Plugins and Embedded Functions and Content</a></li>
            <li><a href="#amendments" className="text-blue-600 hover:underline">Amendments and Updates</a></li>
            <li><a href="#definitions" className="text-blue-600 hover:underline">Definitions</a></li>
          </ul>

          {/* Controller */}
          <h2 id="controller" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Controller
          </h2>
          <div className="bg-gray-50 rounded-lg p-6 mb-8">
            <p className="text-gray-600 leading-relaxed">
              Tim Krebs<br />
              Fürmoosen 39<br />
              85665 Moosach, Germany
            </p>
            <p className="text-gray-600 leading-relaxed mt-4">
              Email: <a href="mailto:timkrebs9@gmail.com" className="text-blue-600 hover:underline">timkrebs9@gmail.com</a>
            </p>
          </div>

          {/* Overview of Processing Activities */}
          <h2 id="overview" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Overview of Processing Activities
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            The following overview summarises the types of data processed and the purposes of their processing and refers to the data subjects concerned.
          </p>

          <h3 className="text-xl font-semibold text-gray-900 mt-8 mb-3">
            Categories of Data Processed
          </h3>
          <ul className="list-disc pl-6 mb-6 space-y-2 text-gray-600">
            <li>Master data</li>
            <li>Contact data</li>
            <li>Content data</li>
            <li>Usage data</li>
            <li>Meta, communication, and procedural data</li>
            <li>Log data</li>
          </ul>

          <h3 className="text-xl font-semibold text-gray-900 mt-8 mb-3">
            Categories of Data Subjects
          </h3>
          <ul className="list-disc pl-6 mb-6 space-y-2 text-gray-600">
            <li>Communication partners</li>
            <li>Users</li>
          </ul>

          <h3 className="text-xl font-semibold text-gray-900 mt-8 mb-3">
            Purposes of Processing
          </h3>
          <ul className="list-disc pl-6 mb-8 space-y-2 text-gray-600">
            <li>Provision of contractual services and fulfilment of contractual obligations</li>
            <li>Communication</li>
            <li>Security measures</li>
            <li>Direct marketing</li>
            <li>Reach measurement</li>
            <li>Organisational and administrative procedures</li>
            <li>Feedback</li>
            <li>Profiles with user-related information</li>
            <li>Registration procedures</li>
            <li>Provision of our Online Services and user-friendliness</li>
            <li>Information technology infrastructure</li>
          </ul>

          {/* Applicable Legal Bases */}
          <h2 id="legal-bases" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Applicable Legal Bases
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Applicable legal bases under the GDPR:</strong> The following provides an overview of the legal bases of the GDPR on which we process personal data. Please note that in addition to the provisions of the GDPR, national data protection regulations may apply in your or our country of residence or domicile. Should more specific legal bases be relevant in individual cases, we will inform you of these in this Privacy Policy.
          </p>
          <ul className="list-disc pl-6 mb-6 space-y-3 text-gray-600">
            <li>
              <strong>Consent (Art. 6(1)(a) GDPR)</strong> – The data subject has given consent to the processing of their personal data for one or more specific purposes.
            </li>
            <li>
              <strong>Performance of a contract and pre-contractual enquiries (Art. 6(1)(b) GDPR)</strong> – Processing is necessary for the performance of a contract to which the data subject is party or in order to take steps at the request of the data subject prior to entering into a contract.
            </li>
            <li>
              <strong>Legitimate interests (Art. 6(1)(f) GDPR)</strong> – Processing is necessary for the purposes of the legitimate interests pursued by the controller or by a third party, except where such interests are overridden by the interests or fundamental rights and freedoms of the data subject which require protection of personal data.
            </li>
          </ul>
          <p className="text-gray-600 leading-relaxed mb-8">
            <strong>National data protection regulations in Germany:</strong> In addition to the data protection regulations of the GDPR, national regulations on data protection apply in Germany. This includes, in particular, the Federal Data Protection Act (Bundesdatenschutzgesetz – BDSG). The BDSG contains specific provisions on the right to information, the right to erasure, the right to object, the processing of special categories of personal data, processing for other purposes, and transmission as well as automated decision-making in individual cases, including profiling. Furthermore, the data protection laws of the individual German federal states may apply.
          </p>

          {/* Security Measures */}
          <h2 id="security" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Security Measures
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            We implement appropriate technical and organisational measures in accordance with the legal requirements, taking into account the state of the art, the costs of implementation, and the nature, scope, context, and purposes of processing, as well as the varying likelihood and severity of the risk to the rights and freedoms of natural persons, to ensure a level of security appropriate to the risk.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            These measures include, in particular, ensuring the confidentiality, integrity, and availability of data by controlling physical and electronic access to the data, as well as access, input, disclosure, ensuring availability, and segregation of data. Furthermore, we have established procedures to ensure the exercise of data subjects&apos; rights, the deletion of data, and responses to data security threats. We also consider the protection of personal data from the outset in the development or selection of hardware, software, and procedures, in accordance with the principle of data protection by design and by default.
          </p>
          <p className="text-gray-600 leading-relaxed mb-8">
            <strong>Securing online connections through TLS/SSL encryption technology (HTTPS):</strong> To protect the data of users transmitted via our online services from unauthorised access, we use TLS/SSL encryption technology. Secure Sockets Layer (SSL) and Transport Layer Security (TLS) are the cornerstones of secure data transmission on the Internet. These technologies encrypt the information transmitted between the website or app and the user&apos;s browser (or between two servers), thereby protecting the data from unauthorised access. TLS, as the more advanced and secure version of SSL, ensures that all data transmissions meet the highest security standards. When a website is secured by an SSL/TLS certificate, this is indicated by the display of HTTPS in the URL. This serves as an indicator to users that their data is being transmitted securely and in encrypted form.
          </p>

          {/* International Data Transfers */}
          <h2 id="international-transfers" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            International Data Transfers
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Data processing in third countries:</strong> If we transfer data to a third country (i.e., outside the European Union (EU) or the European Economic Area (EEA)), or if this occurs in the context of using third-party services or the disclosure or transfer of data to other persons, entities, or companies (which is apparent from the postal address of the respective provider or when explicitly mentioned in this Privacy Policy), this is always done in accordance with the legal requirements.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            For data transfers to the USA, we primarily rely on the Data Privacy Framework (DPF), which was recognised as a secure legal framework by an adequacy decision of the EU Commission on 10 July 2023. Additionally, we have concluded Standard Contractual Clauses with the respective providers, which comply with the requirements of the EU Commission and establish contractual obligations to protect your data.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            This dual safeguard ensures comprehensive protection of your data: The DPF forms the primary level of protection, while the Standard Contractual Clauses serve as additional security. Should changes occur within the DPF framework, the Standard Contractual Clauses will serve as a reliable fallback option. This ensures that your data remains adequately protected even in the event of political or legal changes.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            For individual service providers, we inform you whether they are certified under the DPF and whether Standard Contractual Clauses are in place. Further information on the DPF and a list of certified companies can be found on the website of the U.S. Department of Commerce at <a href="https://www.dataprivacyframework.gov/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://www.dataprivacyframework.gov/</a> (in English).
          </p>
          <p className="text-gray-600 leading-relaxed mb-8">
            For data transfers to other third countries, appropriate safeguards apply, in particular Standard Contractual Clauses, explicit consent, or legally required transfers. Information on third-country transfers and applicable adequacy decisions can be found in the information provided by the EU Commission at: <a href="https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection_en" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection_en</a>
          </p>

          {/* General Information on Data Retention and Deletion */}
          <h2 id="retention" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            General Information on Data Retention and Deletion
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            We delete personal data that we process in accordance with legal requirements as soon as the underlying consent is revoked or there are no further legal grounds for processing. This applies to cases where the original purpose of processing ceases to apply or the data is no longer required. Exceptions to this rule exist where statutory obligations or special interests require longer retention or archiving of the data.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            In particular, data that must be retained for commercial or tax law reasons or whose storage is necessary for legal proceedings or for the protection of the rights of other natural or legal persons must be archived accordingly.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            Our privacy notices contain additional information on the retention and deletion of data that applies specifically to certain processing activities.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            Where multiple indications of retention periods or deletion deadlines for a piece of data exist, the longest period shall always apply. Dates shall only begin to run if they relate to the relevant type of data and if the processing in question requires the retention of the data.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Retention and deletion of data:</strong> The following general periods apply to retention and archiving under German law:
          </p>
          <ul className="list-disc pl-6 mb-6 space-y-3 text-gray-600">
            <li>
              <strong>10 years</strong> – Retention period for books and records, annual financial statements, inventories, management reports, opening balance sheets, and the working instructions and other organisational documents required for their understanding (Section 147(1)(1) in conjunction with Section 147(3) of the German Fiscal Code (AO), Section 14b(1) of the German Value Added Tax Act (UStG), Section 257(1)(1) in conjunction with Section 257(4) of the German Commercial Code (HGB)).
            </li>
            <li>
              <strong>8 years</strong> – Accounting vouchers, such as invoices and cost receipts (Section 147(1)(4) and (4a) in conjunction with Section 147(3) sentence 1 AO and Section 257(1)(4) in conjunction with Section 257(4) HGB).
            </li>
            <li>
              <strong>6 years</strong> – Other business documents: received commercial or business correspondence, reproductions of sent commercial or business correspondence, other documents insofar as they are relevant for taxation, e.g., hourly wage slips, operational accounting records, calculation documents, price labels, as well as payroll accounting documents insofar as they are not already accounting vouchers, and cash register receipts (Section 147(1)(2), (3), (5) in conjunction with Section 147(3) AO, Section 257(1)(2) and (3) in conjunction with Section 257(4) HGB).
            </li>
            <li>
              <strong>3 years</strong> – Data required to consider potential warranty and compensation claims or similar contractual claims and rights, as well as to handle related enquiries, based on prior business experience and standard industry practices, shall be stored for the duration of the regular statutory limitation period of three years (Sections 195, 199 of the German Civil Code (BGB)).
            </li>
          </ul>
          <p className="text-gray-600 leading-relaxed mb-8">
            <strong>Commencement of the period at the end of the year:</strong> If a period does not expressly commence on a specific date and is at least one year, it shall automatically commence at the end of the calendar year in which the event triggering the period occurred. In the case of ongoing contractual relationships in the context of which data is stored, the event triggering the period is the date on which the termination or other termination of the legal relationship takes effect.
          </p>

          {/* Rights of Data Subjects */}
          <h2 id="rights" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Rights of Data Subjects
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Rights of data subjects under the GDPR:</strong> As a data subject, you are entitled to various rights under the GDPR, which arise in particular from Articles 15 to 21 GDPR:
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-3 text-gray-600">
            <li>
              <strong>Right to object:</strong> You have the right to object, on grounds relating to your particular situation, at any time to processing of personal data concerning you which is based on Art. 6(1)(e) or (f) GDPR, including profiling based on those provisions. Where personal data concerning you is processed for direct marketing purposes, you have the right to object at any time to processing of personal data concerning you for such marketing, including profiling to the extent that it is related to such direct marketing.
            </li>
            <li>
              <strong>Right to withdraw consent:</strong> You have the right to withdraw consent at any time.
            </li>
            <li>
              <strong>Right of access:</strong> You have the right to obtain confirmation as to whether or not personal data concerning you is being processed, and, where that is the case, access to the personal data and further information as well as a copy of the data in accordance with the legal requirements.
            </li>
            <li>
              <strong>Right to rectification:</strong> You have the right, in accordance with the legal requirements, to obtain the completion of data concerning you or the rectification of inaccurate data concerning you.
            </li>
            <li>
              <strong>Right to erasure and restriction of processing:</strong> You have the right, in accordance with the legal requirements, to demand that data concerning you be erased without undue delay, or alternatively, in accordance with the legal requirements, to demand restriction of the processing of the data.
            </li>
            <li>
              <strong>Right to data portability:</strong> You have the right to receive the data concerning you, which you have provided to us, in a structured, commonly used and machine-readable format in accordance with the legal requirements, or to demand that it be transmitted to another controller.
            </li>
            <li>
              <strong>Right to lodge a complaint with a supervisory authority:</strong> Without prejudice to any other administrative or judicial remedy, you have the right to lodge a complaint with a supervisory authority, in particular in the Member State of your habitual residence, your place of work or the place of the alleged infringement, if you consider that the processing of personal data relating to you infringes the GDPR.
            </li>
          </ul>

          {/* Provision of the Online Services and Web Hosting */}
          <h2 id="hosting" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Provision of the Online Services and Web Hosting
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            We process users&apos; data in order to provide them with our online services. For this purpose, we process the user&apos;s IP address, which is necessary to transmit the content and functions of our online services to the user&apos;s browser or device.
          </p>
          <ul className="list-disc pl-6 mb-6 space-y-3 text-gray-600">
            <li>
              <strong>Categories of data processed:</strong> Usage data (e.g., page views and dwell time, click paths, usage intensity and frequency, device types and operating systems used, interactions with content and functions); meta, communication, and procedural data (e.g., IP addresses, timestamps, identification numbers, persons involved); log data (e.g., log files relating to logins or data retrieval or access times).
            </li>
            <li>
              <strong>Data subjects:</strong> Users (e.g., website visitors, users of online services).
            </li>
            <li>
              <strong>Purposes of processing:</strong> Provision of our Online Services and user-friendliness; information technology infrastructure (operation and provision of information systems and technical devices (computers, servers, etc.)); security measures.
            </li>
            <li>
              <strong>Retention and deletion:</strong> Deletion in accordance with the information in the section &quot;General Information on Data Retention and Deletion&quot;.
            </li>
            <li>
              <strong>Legal basis:</strong> Legitimate interests (Art. 6(1)(f) GDPR).
            </li>
          </ul>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Further information on processing activities, procedures, and services:</strong>
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-3 text-gray-600">
            <li>
              <strong>Provision of Online Services on rented storage space:</strong> For the provision of our Online Services, we use storage space, computing capacity, and software that we rent or otherwise obtain from a corresponding server provider (also known as a &quot;web host&quot;); <strong>Legal basis:</strong> Legitimate interests (Art. 6(1)(f) GDPR).
            </li>
            <li>
              <strong>Collection of access data and log files:</strong> Access to our Online Services is logged in the form of so-called &quot;server log files&quot;. Server log files may include the address and name of the web pages and files accessed, date and time of access, data volumes transferred, notification of successful retrieval, browser type and version, the user&apos;s operating system, referrer URL (the previously visited page), and, as a rule, IP addresses and the requesting provider. Server log files can be used for security purposes, e.g., to prevent server overload (particularly in the case of abusive attacks, so-called DDoS attacks), and to ensure server load and stability; <strong>Legal basis:</strong> Legitimate interests (Art. 6(1)(f) GDPR). <strong>Deletion of data:</strong> Log file information is stored for a maximum of 30 days and then deleted or anonymised. Data whose further retention is required for evidentiary purposes is exempt from deletion until the respective incident has been finally resolved.
            </li>
          </ul>

          {/* Registration, Login, and User Account */}
          <h2 id="registration" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Registration, Login, and User Account
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            Users may create a user account. During registration, users are provided with the required mandatory information and this is processed for the purpose of providing the user account on the basis of contractual obligation. The data processed includes, in particular, login information (username, password, and an email address).
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            During the use of our registration and login functions and the user account, we store the IP address and the time of the respective user action. Storage is based on our legitimate interests as well as those of users in protection against misuse and other unauthorised use. This data is generally not passed on to third parties unless it is necessary for the pursuit of our claims or there is a legal obligation to do so.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            Users may be informed by email about events relevant to their user account, such as technical changes.
          </p>
          <ul className="list-disc pl-6 mb-6 space-y-3 text-gray-600">
            <li>
              <strong>Categories of data processed:</strong> Master data (e.g., full name, residential address, contact information, customer number, etc.); contact data (e.g., postal and email addresses or telephone numbers); content data (e.g., textual or pictorial messages and contributions as well as the information relating to them, such as details of authorship or time of creation); usage data (e.g., page views and dwell time, click paths, usage intensity and frequency, device types and operating systems used, interactions with content and functions); log data (e.g., log files relating to logins or data retrieval or access times).
            </li>
            <li>
              <strong>Data subjects:</strong> Users (e.g., website visitors, users of online services).
            </li>
            <li>
              <strong>Purposes of processing:</strong> Provision of contractual services and fulfilment of contractual obligations; security measures; organisational and administrative procedures; provision of our Online Services and user-friendliness.
            </li>
            <li>
              <strong>Retention and deletion:</strong> Deletion in accordance with the information in the section &quot;General Information on Data Retention and Deletion&quot;. Deletion upon termination.
            </li>
            <li>
              <strong>Legal basis:</strong> Performance of a contract and pre-contractual enquiries (Art. 6(1)(b) GDPR); legitimate interests (Art. 6(1)(f) GDPR).
            </li>
          </ul>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Further information on processing activities, procedures, and services:</strong>
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-3 text-gray-600">
            <li>
              <strong>Registration with pseudonyms:</strong> Users may use pseudonyms instead of their real names as usernames; <strong>Legal basis:</strong> Performance of a contract and pre-contractual enquiries (Art. 6(1)(b) GDPR).
            </li>
            <li>
              <strong>User profiles are not public:</strong> User profiles are not publicly visible or accessible.
            </li>
            <li>
              <strong>Deletion of data upon termination:</strong> When users have terminated their user account, their data relating to the user account will be deleted, subject to any legal permission, obligation, or consent of the users; <strong>Legal basis:</strong> Performance of a contract and pre-contractual enquiries (Art. 6(1)(b) GDPR).
            </li>
            <li>
              <strong>No obligation to retain data:</strong> It is the responsibility of users to back up their data before the end of the contract upon termination. We are entitled to irretrievably delete all user data stored during the term of the contract; <strong>Legal basis:</strong> Performance of a contract and pre-contractual enquiries (Art. 6(1)(b) GDPR).
            </li>
          </ul>

          {/* Single Sign-On Authentication */}
          <h2 id="sso" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Single Sign-On Authentication
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            &quot;Single sign-on&quot; or &quot;single sign-on login or authentication&quot; refers to procedures that allow users to log in to our Online Services using a user account with a single sign-on provider (e.g., a social network). The prerequisite for single sign-on authentication is that users are registered with the respective single sign-on provider and enter the required access data in the online form provided for this purpose, or are already logged in with the single sign-on provider and confirm the single sign-on login via a button.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            Authentication takes place directly with the respective single sign-on provider. In the context of such authentication, we receive a user ID with the information that the user is logged in under this user ID with the respective single sign-on provider and an ID that cannot be used by us for other purposes (so-called &quot;user handle&quot;). Whether additional data is transmitted to us depends solely on the single sign-on procedure used, on the data releases selected during authentication, and also on which data users have released in the privacy or other settings of their user account with the single sign-on provider. Depending on the single sign-on provider and the user&apos;s choice, different data may be involved; usually this includes the email address and the username. The password entered as part of the single sign-on procedure with the single sign-on provider is neither visible to us nor stored by us.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            Users are asked to note that their information stored with us may be automatically synchronised with their user account with the single sign-on provider, but this is not always possible or does not always occur. For example, if users&apos; email addresses change, they must manually change them in their user account with us.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            We may use single sign-on login, if agreed with the users, in the context of or prior to the performance of the contract, insofar as users have been asked to do so, process it in the context of consent, and otherwise use it on the basis of our legitimate interests and the interests of users in an effective and secure login system.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            Should users decide that they no longer wish to use the link to their user account with the single sign-on provider for the single sign-on procedure, they must dissolve this connection within their user account with the single sign-on provider. If users wish to delete their data with us, they must terminate their registration with us.
          </p>
          <ul className="list-disc pl-6 mb-6 space-y-3 text-gray-600">
            <li>
              <strong>Categories of data processed:</strong> Master data (e.g., full name, residential address, contact information, customer number, etc.); contact data (e.g., postal and email addresses or telephone numbers); usage data (e.g., page views and dwell time, click paths, usage intensity and frequency, device types and operating systems used, interactions with content and functions); meta, communication, and procedural data (e.g., IP addresses, timestamps, identification numbers, persons involved).
            </li>
            <li>
              <strong>Data subjects:</strong> Users (e.g., website visitors, users of online services).
            </li>
            <li>
              <strong>Purposes of processing:</strong> Provision of contractual services and fulfilment of contractual obligations; security measures; login procedures; provision of our Online Services and user-friendliness.
            </li>
            <li>
              <strong>Retention and deletion:</strong> Deletion in accordance with the information in the section &quot;General Information on Data Retention and Deletion&quot;. Deletion upon termination.
            </li>
            <li>
              <strong>Legal basis:</strong> Performance of a contract and pre-contractual enquiries (Art. 6(1)(b) GDPR); legitimate interests (Art. 6(1)(f) GDPR).
            </li>
          </ul>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Further information on processing activities, procedures, and services:</strong>
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-3 text-gray-600">
            <li>
              <strong>Google Single Sign-On:</strong> Authentication services for user logins, provision of single sign-on functions, management of identity information, and application integrations; <strong>Service provider:</strong> Google Ireland Limited, Gordon House, Barrow Street, Dublin 4, Ireland; <strong>Legal basis:</strong> Legitimate interests (Art. 6(1)(f) GDPR); <strong>Website:</strong> <a href="https://www.google.de" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://www.google.de</a>; <strong>Privacy policy:</strong> <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://policies.google.com/privacy</a>; <strong>Basis for third-country transfer:</strong> Data Privacy Framework (DPF). <strong>Opt-out option:</strong> Settings for the display of advertisements: <a href="https://myadcenter.google.com/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://myadcenter.google.com/</a>
            </li>
          </ul>

          {/* Contact and Enquiry Management */}
          <h2 id="contact" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Contact and Enquiry Management
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            When contacting us (e.g., by post, contact form, email, telephone, or via social media) and in the context of existing user and business relationships, the information of the enquiring persons is processed insofar as this is necessary to answer the contact enquiries and any requested measures.
          </p>
          <ul className="list-disc pl-6 mb-6 space-y-3 text-gray-600">
            <li>
              <strong>Categories of data processed:</strong> Contact data (e.g., postal and email addresses or telephone numbers); content data (e.g., textual or pictorial messages and contributions as well as the information relating to them, such as details of authorship or time of creation); meta, communication, and procedural data (e.g., IP addresses, timestamps, identification numbers, persons involved).
            </li>
            <li>
              <strong>Data subjects:</strong> Communication partners.
            </li>
            <li>
              <strong>Purposes of processing:</strong> Communication; organisational and administrative procedures; feedback (e.g., collecting feedback via online form); provision of our Online Services and user-friendliness.
            </li>
            <li>
              <strong>Retention and deletion:</strong> Deletion in accordance with the information in the section &quot;General Information on Data Retention and Deletion&quot;.
            </li>
            <li>
              <strong>Legal basis:</strong> Legitimate interests (Art. 6(1)(f) GDPR); performance of a contract and pre-contractual enquiries (Art. 6(1)(b) GDPR).
            </li>
          </ul>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Further information on processing activities, procedures, and services:</strong>
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-3 text-gray-600">
            <li>
              <strong>Contact form:</strong> When contacting us via our contact form, by email, or other means of communication, we process the personal data transmitted to us in order to answer and process the respective enquiry. This usually includes information such as name, contact information, and, where applicable, further information that is communicated to us and is required for appropriate processing. We use this data exclusively for the stated purpose of contact and communication; <strong>Legal basis:</strong> Performance of a contract and pre-contractual enquiries (Art. 6(1)(b) GDPR); legitimate interests (Art. 6(1)(f) GDPR).
            </li>
          </ul>

          {/* Newsletter and Electronic Notifications */}
          <h2 id="newsletter" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Newsletter and Electronic Notifications
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            We send newsletters, emails, and other electronic notifications (hereinafter &quot;Newsletter&quot;) only with the consent of the recipients or on a legal basis. If the content of the newsletter is described in the context of a registration for the newsletter, this content is decisive for the consent of the users. For registration to our newsletter, it is usually sufficient to provide your email address. However, in order to provide you with a personalised service, we may ask for your name for personal address in the newsletter or for further information if this is necessary for the purpose of the newsletter.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Deletion and restriction of processing:</strong> We may store unsubscribed email addresses for up to three years on the basis of our legitimate interests before deleting them in order to be able to prove formerly given consent. The processing of this data is limited to the purpose of a potential defence against claims. An individual deletion request is possible at any time, provided that the former existence of consent is confirmed at the same time. In the case of obligations to permanently observe objections, we reserve the right to store the email address solely for this purpose in a blocklist.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            The logging of the registration procedure is carried out on the basis of our legitimate interests for the purpose of proving its proper execution. If we commission a service provider to send emails, this is done on the basis of our legitimate interests in an efficient and secure sending system.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Content:</strong> Information on current news on stocks and the economy.
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-3 text-gray-600">
            <li>
              <strong>Categories of data processed:</strong> Master data (e.g., full name, residential address, contact information, customer number, etc.); contact data (e.g., postal and email addresses or telephone numbers); meta, communication, and procedural data (e.g., IP addresses, timestamps, identification numbers, persons involved).
            </li>
            <li>
              <strong>Data subjects:</strong> Communication partners.
            </li>
            <li>
              <strong>Purposes of processing:</strong> Direct marketing (e.g., by email or post).
            </li>
            <li>
              <strong>Legal basis:</strong> Consent (Art. 6(1)(a) GDPR).
            </li>
            <li>
              <strong>Opt-out option:</strong> You can cancel the receipt of our newsletter at any time, i.e., revoke your consent or object to further receipt. You will find a link to cancel the newsletter either at the end of each newsletter or can use one of the contact options stated above, preferably email, for this purpose.
            </li>
          </ul>

          {/* Web Analytics, Monitoring, and Optimisation */}
          <h2 id="analytics" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Web Analytics, Monitoring, and Optimisation
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            Web analytics (also referred to as &quot;reach measurement&quot;) is used to evaluate the visitor traffic of our Online Services and may include behaviour, interests, or demographic information about visitors, such as age or gender, as pseudonymous values. With the help of reach analysis, we can, for example, recognise at what time our Online Services or their functions or content are most frequently used, or invite re-use. We can also understand which areas require optimisation.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            In addition to web analytics, we may also use testing procedures, for example, to test and optimise different versions of our Online Services or their components.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            Unless otherwise stated below, profiles, i.e., data summarised for a usage process, may be created for these purposes and information may be stored in a browser or terminal device and then read out. The information collected includes, in particular, websites visited and elements used there, as well as technical information such as the browser used, the computer system used, and information on usage times. If users have consented to the collection of their location data to us or to the providers of the services we use, location data may also be processed.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            Furthermore, the IP addresses of users are stored. However, we use an IP masking procedure (i.e., pseudonymisation by shortening the IP address) to protect users. In general, no clear user data (such as email addresses or names) is stored in the context of web analytics, A/B testing, and optimisation, but only pseudonyms. This means that we, as well as the providers of the software used, do not know the actual identity of the users, but only the information stored in their profiles for the purposes of the respective procedures.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Information on legal bases:</strong> If we ask users for their consent to use third-party providers, the legal basis of data processing is consent. Otherwise, user data is processed on the basis of our legitimate interests (i.e., interest in efficient, economical, and recipient-friendly services). In this context, we would also like to draw your attention to the information on the use of cookies in this Privacy Policy.
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-3 text-gray-600">
            <li>
              <strong>Categories of data processed:</strong> Usage data (e.g., page views and dwell time, click paths, usage intensity and frequency, device types and operating systems used, interactions with content and functions); meta, communication, and procedural data (e.g., IP addresses, timestamps, identification numbers, persons involved).
            </li>
            <li>
              <strong>Data subjects:</strong> Users (e.g., website visitors, users of online services).
            </li>
            <li>
              <strong>Purposes of processing:</strong> Reach measurement (e.g., access statistics, recognition of returning visitors); profiles with user-related information (creation of user profiles).
            </li>
            <li>
              <strong>Retention and deletion:</strong> Deletion in accordance with the information in the section &quot;General Information on Data Retention and Deletion&quot;. Storage of cookies for up to 2 years (unless otherwise stated, cookies and similar storage methods may be stored on users&apos; devices for a period of two years).
            </li>
            <li>
              <strong>Security measures:</strong> IP masking (pseudonymisation of the IP address).
            </li>
            <li>
              <strong>Legal basis:</strong> Consent (Art. 6(1)(a) GDPR); legitimate interests (Art. 6(1)(f) GDPR).
            </li>
          </ul>

          {/* Plugins and Embedded Functions and Content */}
          <h2 id="plugins" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Plugins and Embedded Functions and Content
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            We integrate functional and content elements into our Online Services that are obtained from the servers of their respective providers (hereinafter referred to as &quot;third-party providers&quot;). These may include, for example, graphics, videos, or city maps (hereinafter uniformly referred to as &quot;content&quot;).
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            Integration always requires that the third-party providers of this content process the IP address of users, as without the IP address they would not be able to send the content to their browser. The IP address is therefore required for the display of this content or function. We endeavour to use only content whose respective providers use the IP address solely for the delivery of the content. Third-party providers may also use so-called pixel tags (invisible graphics, also known as &quot;web beacons&quot;) for statistical or marketing purposes. The &quot;pixel tags&quot; can be used to evaluate information such as visitor traffic on the pages of this website. The pseudonymous information may also be stored in cookies on the user&apos;s device and may contain, among other things, technical information about the browser and operating system, referring websites, time of visit, and other information about the use of our Online Services, as well as being linked to such information from other sources.
          </p>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Information on legal bases:</strong> If we ask users for their consent to the use of third-party providers, the legal basis of data processing is consent. Otherwise, user data is processed on the basis of our legitimate interests (i.e., interest in efficient, economical, and recipient-friendly services). In this context, we would also like to draw your attention to the information on the use of cookies in this Privacy Policy.
          </p>
          <ul className="list-disc pl-6 mb-6 space-y-3 text-gray-600">
            <li>
              <strong>Categories of data processed:</strong> Usage data (e.g., page views and dwell time, click paths, usage intensity and frequency, device types and operating systems used, interactions with content and functions); meta, communication, and procedural data (e.g., IP addresses, timestamps, identification numbers, persons involved).
            </li>
            <li>
              <strong>Data subjects:</strong> Users (e.g., website visitors, users of online services).
            </li>
            <li>
              <strong>Purposes of processing:</strong> Provision of our Online Services and user-friendliness.
            </li>
            <li>
              <strong>Retention and deletion:</strong> Deletion in accordance with the information in the section &quot;General Information on Data Retention and Deletion&quot;. Storage of cookies for up to 2 years (unless otherwise stated, cookies and similar storage methods may be stored on users&apos; devices for a period of two years).
            </li>
            <li>
              <strong>Legal basis:</strong> Consent (Art. 6(1)(a) GDPR); legitimate interests (Art. 6(1)(f) GDPR).
            </li>
          </ul>
          <p className="text-gray-600 leading-relaxed mb-4">
            <strong>Further information on processing activities, procedures, and services:</strong>
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-3 text-gray-600">
            <li>
              <strong>Google Fonts (obtained from Google server):</strong> Obtaining fonts (and symbols) for the purpose of a technically secure, maintenance-free, and efficient use of fonts and symbols with regard to up-to-dateness and loading times, their uniform presentation, and consideration of possible licensing restrictions. The provider of the fonts is informed of the user&apos;s IP address so that the fonts can be made available in the user&apos;s browser. In addition, technical data (language settings, screen resolution, operating system, hardware used) are transmitted, which are necessary for the provision of the fonts depending on the devices used and the technical environment. This data may be processed on a server of the font provider in the USA – When visiting our Online Services, users&apos; browsers send their browser HTTP requests to the Google Fonts Web API (i.e., a software interface for retrieving fonts). The Google Fonts Web API provides users with the Cascading Style Sheets (CSS) of Google Fonts and then the fonts specified in the CSS. These HTTP requests include (1) the IP address used by the respective user to access the Internet, (2) the requested URL on the Google server, and (3) HTTP headers, including the user agent, which describes the browser and operating system versions of website visitors, as well as the referring URL (i.e., the web page on which the Google font is to be displayed). IP addresses are neither logged nor stored on Google servers and are not analysed. The Google Fonts Web API logs details of HTTP requests (requested URL, user agent, and referring URL). Access to this data is restricted and strictly controlled. The requested URL identifies the font families for which the user wants to load fonts. This data is logged so that Google can determine how often a particular font family is requested. The Google Fonts Web API requires the user agent to adapt the font generated for the respective browser type. The user agent is logged primarily for debugging and is used to generate aggregated usage statistics that measure the popularity of font families. These aggregated usage statistics are published on the Google Fonts Analytics page. Finally, the referring URL is logged so that the data can be used for production maintenance and an aggregated report on the top integrations based on the number of font requests can be generated. According to Google, Google does not use any of the information collected by Google Fonts to create end-user profiles or to display targeted advertisements; <strong>Service provider:</strong> Google Ireland Limited, Gordon House, Barrow Street, Dublin 4, Ireland; <strong>Legal basis:</strong> Legitimate interests (Art. 6(1)(f) GDPR); <strong>Website:</strong> <a href="https://fonts.google.com/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://fonts.google.com/</a>; <strong>Privacy policy:</strong> <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://policies.google.com/privacy</a>; <strong>Basis for third-country transfer:</strong> Data Privacy Framework (DPF). <strong>Further information:</strong> <a href="https://developers.google.com/fonts/faq/privacy?hl=en" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">https://developers.google.com/fonts/faq/privacy?hl=en</a>
            </li>
          </ul>

          {/* Amendments and Updates */}
          <h2 id="amendments" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Amendments and Updates
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            We ask you to regularly inform yourself about the content of our Privacy Policy. We adapt the Privacy Policy as soon as changes in the data processing carried out by us make this necessary. We will inform you as soon as the changes require an act of cooperation on your part (e.g., consent) or other individual notification.
          </p>
          <p className="text-gray-600 leading-relaxed mb-8">
            If we provide addresses and contact information of companies and organisations in this Privacy Policy, please note that the addresses may change over time and ask you to check the information before contacting us.
          </p>

          {/* Definitions */}
          <h2 id="definitions" className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Definitions
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            This section provides an overview of the terms used in this Privacy Policy. Where the terms are legally defined, their legal definitions shall apply. The following explanations, however, are primarily intended to aid understanding.
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-3 text-gray-600">
            <li>
              <strong>Master data:</strong> Master data includes essential information necessary for the identification and management of contractual partners, user accounts, profiles, and similar assignments. This data may include, among others, personal and demographic information such as names, contact information (addresses, telephone numbers, email addresses), dates of birth, and specific identifiers (user IDs). Master data forms the basis for any formal interaction between persons and services, institutions, or systems by enabling unambiguous assignment and communication.
            </li>
            <li>
              <strong>Content data:</strong> Content data includes information generated in the course of creating, editing, and publishing content of all kinds. This category of data may include texts, images, videos, audio files, and other multimedia content published on various platforms and media. Content data is not limited to the actual content itself but also includes metadata that provides information about the content itself, such as tags, descriptions, author information, and publication dates.
            </li>
            <li>
              <strong>Contact data:</strong> Contact data is essential information that enables communication with individuals or organisations. It includes, among others, telephone numbers, postal addresses, and email addresses, as well as means of communication such as social media handles and instant messaging identifiers.
            </li>
            <li>
              <strong>Meta, communication, and procedural data:</strong> Meta, communication, and procedural data are categories that contain information about how data is processed, transmitted, and managed. Metadata, also known as data about data, includes information that describes the context, origin, and structure of other data. It may include information on file size, creation date, author of a document, and change histories. Communication data captures the exchange of information between users via various channels, such as email traffic, call logs, messages on social networks, and chat histories, including the persons involved, timestamps, and transmission paths. Procedural data describes the processes and procedures within systems or organisations, including workflow documentation, logs of transactions and activities, and audit logs used to trace and verify operations.
            </li>
            <li>
              <strong>Usage data:</strong> Usage data refers to information that captures how users interact with digital products, services, or platforms. This data encompasses a wide range of information that shows how users use applications, which features they prefer, how long they stay on certain pages, and the paths they navigate through an application. Usage data may also include frequency of use, timestamps of activities, IP addresses, device information, and location data. It is particularly valuable for analysing user behaviour, optimising user experiences, personalising content, and improving products or services. In addition, usage data plays a crucial role in identifying trends, preferences, and potential problem areas within digital offerings.
            </li>
            <li>
              <strong>Personal data:</strong> &quot;Personal data&quot; means any information relating to an identified or identifiable natural person (hereinafter &quot;data subject&quot;); an identifiable natural person is one who can be identified, directly or indirectly, in particular by reference to an identifier such as a name, an identification number, location data, an online identifier (e.g., cookie) or to one or more factors specific to the physical, physiological, genetic, mental, economic, cultural, or social identity of that natural person.
            </li>
            <li>
              <strong>Profiles with user-related information:</strong> The processing of &quot;profiles with user-related information&quot;, or &quot;profiles&quot; for short, includes any form of automated processing of personal data consisting of using such personal data to evaluate certain personal aspects relating to a natural person (depending on the type of profiling, this may include various information relating to demographics, behaviour, and interests, such as interaction with websites and their content, etc.) to analyse or predict them (e.g., interests in certain content or products, click behaviour on a website, or location). Cookies and web beacons are often used for profiling purposes.
            </li>
            <li>
              <strong>Log data:</strong> Log data is information about events or activities that have been logged in a system or network. This data typically contains information such as timestamps, IP addresses, user actions, error messages, and other details about the use or operation of a system. Log data is often used to analyse system problems, for security monitoring, or to generate performance reports.
            </li>
            <li>
              <strong>Reach measurement:</strong> Reach measurement (also known as web analytics) is used to evaluate the visitor traffic of an online service and may include the behaviour or interests of visitors in certain information, such as website content. With the help of reach analysis, operators of online services can, for example, recognise at what time users visit their websites and what content they are interested in. This enables them, for example, to better adapt the content of the websites to the needs of their visitors. For reach analysis purposes, pseudonymous cookies and web beacons are often used to recognise returning visitors and thus obtain more precise analyses of the use of an online service.
            </li>
            <li>
              <strong>Controller:</strong> &quot;Controller&quot; means the natural or legal person, public authority, agency, or other body which, alone or jointly with others, determines the purposes and means of the processing of personal data.
            </li>
            <li>
              <strong>Processing:</strong> &quot;Processing&quot; means any operation or set of operations which is performed on personal data or on sets of personal data, whether or not by automated means. The term is broad and covers virtually any handling of data, whether collecting, evaluating, storing, transmitting, or deleting.
            </li>
          </ul>

          {/* Footer */}
          <p className="text-gray-400 text-sm text-center mt-16 pt-8 border-t border-gray-100">
            Created with the free Privacy Policy Generator by Dr. Thomas Schwenke
          </p>

        </div>
      </section>
    </main>
  )
}