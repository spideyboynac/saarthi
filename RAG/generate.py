import csv
import random

# Seed for reproducible high-quality output generation
random.seed(2026)

scenarios_map = {
    "labour_rights": [
        "wrongful_termination", "unpaid_wages", "casual_labor_regularization",
        "workplace_injury_compensation", "pf_gratuity_denial", "maternity_benefit_denial",
        "minimum_wage_violation", "contract_vs_permanent_dispute", "migrant_bonded_labor_exploitation",
        "overtime_wage_denial", "illegal_lockout_closure", "trade_union_victimization",
        "apprentice_exploitation", "occupational_health_safety_violation"
    ],
    "crime": [
        "assault_hurt", "criminal_intimidation", "theft", "cheating_fraud",
        "criminal_trespass", "public_nuisance", "extortion_demands",
        "mischief_property_damage", "forgery_falsification_documents",
        "unlawful_assembly_rioting", "receiving_stolen_property"
    ],
    "women_violence_marriage": [
        "domestic_violence_498a", "dowry_harassment", "maintenance_125_crpc",
        "child_custody", "posh_workplace_harassment", "protection_orders",
        "marital_property_rights", "restitution_conjugal_rights",
        "interim_maintenance_enhancement", "maternal_right_to_residence", "desertion_cruelty_divorce"
    ],
    "land_dispute": [
        "title_disputes", "land_acquisition_compensation", "tenancy_eviction",
        "boundary_disputes", "inheritance_partition", "encroachments",
        "adverse_possession", "government_land_allotment", "easementary_rights_way",
        "mortgage_redemption_dispute", "revenue_mutation_record_correction",
        "common_pasture_gauchar_dispute", "land_ceiling_excess_surrender"
    ]
}

court_levels = ["District Court", "High Court", "Supreme Court"]
decisions = ["Accepted", "Rejected", "Partial"]

occupations = [
    "brick kiln loader", "tea garden supervisor", "textile weaver", "tractor driver", 
    "warehouse helper", "sanitation worker", "construction mason", "primary health worker", 
    "sugar mill technician", "plantation laborer", "stone quarry miner", "rice mill operator",
    "garment worker", "electrical maintenance assistant", "handloom worker"
]

land_measures = ["1.2 acres", "2.5 acres", "4.0 acres", "5 bighas", "0.8 acres", "12 bighas", "3.5 acres", "2.0 bighas"]
relations = ["co-sharer brother", "paternal uncle", "neighboring landholder", "local moneylender", "estranged spouse", "former business partner", "village contractor"]

def generate_case_narrative(topic, scenario, court_level, decision):
    occ = random.choice(occupations)
    land = random.choice(land_measures)
    rel = random.choice(relations)
    
    if topic == "labour_rights":
        if scenario == "wrongful_termination":
            return f"Synthetic Case: A {occ} with continuous service for over 240 days in a calendar year was orally discharged without written notice, prior inquiry, or retrenchment compensation mandated under Section 25F of the Industrial Disputes Act. Management alleged performance issues without holding a domestic inquiry. {court_level} examined muster rolls and pay slips, holding the termination illegal and directing statutory relief. Ruling: {decision}."
        elif scenario == "unpaid_wages":
            return f"Synthetic Case: Group of rural workers deployed at a processing facility petitioned for 5 months of accrued unpaid wages. The employer claimed financial distress and crop yield loss justified delayed disbursements. {court_level} affirmed that statutory minimum wage obligations under the Payment of Wages framework cannot be deferred or contingent on commercial profitability. Ruling: {decision}."
        elif scenario == "casual_labor_regularization":
            return f"Synthetic Case: Daily-wage workers engaged continuously for over 8 years against sanctioned public works vacancies sought absorption into regular cadre. State authorities argued the initial recruitment lacked formal selection process. {court_level} evaluated unbroken service records and directed consideration for regularization under applicable public employment policies. Ruling: {decision}."
        elif scenario == "workplace_injury_compensation":
            return f"Synthetic Case: A {occ} suffered severe partial disability due to an unshielded machine unit at a rural plant. Management offered minor ex-gratia assistance while denying statutory liability under the Employee's Compensation Act. {court_level} evaluated medical disability certificates and loss of earning capacity, ordering full statutory compensation. Ruling: {decision}."
        elif scenario == "pf_gratuity_denial":
            return f"Synthetic Case: Retired seasonal employee denied terminal gratuity benefits on grounds that seasonal employment interrupted continuous service requirements. {court_level} held that seasonal engagements meeting statutory minimum operational days satisfy the threshold under the Payment of Gratuity Act. Ruling: {decision}."
        elif scenario == "maternity_benefit_denial":
            return f"Synthetic Case: Contractual female {occ} was denied 26 weeks paid maternity leave and subsequently terminated upon applying for leave. Employer relied on private contract terms excluding statutory maternity benefits. {court_level} ruled that statutory entitlements under the Maternity Benefit Act override private contractual restrictions. Ruling: {decision}."
        elif scenario == "minimum_wage_violation":
            return f"Synthetic Case: Agricultural laborers demonstrated that cash wages paid by a commercial farm were lower than state-notified minimum wage rates, with unnotified deductions made for basic shelter. {court_level} prohibited unnotified wage deductions and directed back-pay calculation based on official minimum wage notifications. Ruling: {decision}."
        elif scenario == "contract_vs_permanent_dispute":
            return f"Synthetic Case: Assembly line workers engaged via an intermediary labor contractor performed core operational tasks alongside permanent workers for half pay. {court_level} found the contract labor arrangement to be a sham mechanism designed to evade equal pay mandates, directing parity in remuneration. Ruling: {decision}."
        elif scenario == "migrant_bonded_labor_exploitation":
            return f"Synthetic Case: Inter-state migrant laborers detained at a brick kiln due to alleged advance debt obligations filed for relief under the Bonded Labour System (Abolition) Act. {court_level} directed immediate release, cancellation of alleged debts, and state rehabilitation assistance. Ruling: {decision}."
        elif scenario == "overtime_wage_denial":
            return f"Synthetic Case: Factory workers required to work 12-hour daily shifts without overtime payment petitioned under factories welfare rules. {court_level} verified shift logbooks and ordered payment of double-rate statutory overtime wages. Ruling: {decision}."
        elif scenario == "illegal_lockout_closure":
            return f"Synthetic Case: Industrial unit management instituted sudden site closure without serving 60 days prior statutory notice to the labor commissioner. {court_level} declared the lockout illegal and awarded full wage continuity during the closure period. Ruling: {decision}."
        elif scenario == "trade_union_victimization":
            return f"Synthetic Case: Union office-bearers were target-transferred to remote sites immediately following the submission of a collective bargaining charter. {court_level} held the transfers to be unfair labor practice intended to suppress union activities and issued stay orders. Ruling: {decision}."
        elif scenario == "apprentice_exploitation":
            return f"Synthetic Case: Trainees engaged under apprentice designations were deployed on core production machinery for over 3 years without formal training or stipend adjustment. {court_level} recognized them as regular workmen entitled to statutory wage scales. Ruling: {decision}."
        else:
            return f"Synthetic Case: Quarry miners exposed to toxic dust petitioned regarding lack of personal protective equipment and regular health check-ups mandated under mines safety regulations. {court_level} ordered immediate safety compliance, medical monitoring, and compensation for affected workers. Ruling: {decision}."

    elif topic == "crime":
        if scenario == "assault_hurt":
            return f"Synthetic Case: Altercation between agricultural neighbors over irrigation water flow led to voluntary causing of hurt with blunt implements. Defense argued private defense without supporting physical evidence. {court_level} relied on medical injury certificates and neutral eyewitness statements to assess criminal liability for hurt. Ruling: {decision}."
        elif scenario == "criminal_intimidation":
            return f"Synthetic Case: Complainant reported repeated verbal threats of bodily harm and destruction of standing crops made by a {rel} during loan recovery demands. Neutral witness testimony corroborated the threats. {court_level} analyzed whether the acts constituted criminal intimidation intended to cause alarm. Ruling: {decision}."
        elif scenario == "theft":
            return f"Synthetic Case: Allegation of theft involving agricultural water pump machinery from a field shed. Stolen equipment was subsequently recovered from the accused's premises based on serial identification marks. {court_level} examined possession of stolen property and chain of custody evidence. Ruling: {decision}."
        elif scenario == "cheating_fraud":
            return f"Synthetic Case: Accused collected advance cash deposits from rural youth promising guaranteed government job placements using forged sanction letters. {court_level} reviewed financial transaction evidence and established dishonest inducement from inception under cheating provisions. Ruling: {decision}."
        elif scenario == "criminal_trespass":
            return f"Synthetic Case: Accused forcibly entered fenced private farm property post-sunset following a boundary altercation, attempting to alter land boundary markers. {court_level} verified unauthorized physical entry with intent to commit an offense or intimidate the lawful possessor. Ruling: {decision}."
        elif scenario == "public_nuisance":
            return f"Synthetic Case: Residents petitioned against an unauthorized stone crushing unit operating near residential dwellings, citing excessive dust and noise pollution beyond permissible health limits. {court_level} ordered compliance with environmental standards and public nuisance restrictions. Ruling: {decision}."
        elif scenario == "extortion_demands":
            return f"Synthetic Case: Local shopkeeper filed complaint alleging monthly unlawful monetary demands under threat of business disruption by a village group. {court_level} evaluated digital call recordings and witness testimony to affirm extortion charges. Ruling: {decision}."
        elif scenario == "mischief_property_damage":
            return f"Synthetic Case: Accused intentionally breached an embankment wall during heavy rains, causing flooding and damage to complainant's standing standing crops. {court_level} assessed physical inspection reports establishing intentional property damage under mischief provisions. Ruling: {decision}."
        elif scenario == "forgery_falsification_documents":
            return f"Synthetic Case: Forged signature discovered on a rural land sale deed submitted for revenue registration. Forensic handwriting analysis confirmed falsification. {court_level} held deed void and initiated criminal proceedings for document forgery. Ruling: {decision}."
        elif scenario == "unlawful_assembly_rioting":
            return f"Synthetic Case: Group altercation during village fair led to public property damage and minor injuries. Prosecution established common object of unlawful assembly. {court_level} evaluated individual roles and witness identification. Ruling: {decision}."
        else:
            return f"Synthetic Case: Seizure of stolen solar panel equipment from a trader's shop. Trader claimed bona fide purchase without knowledge of theft. {court_level} evaluated purchase price disparity and lack of valid bills to establish constructive knowledge under stolen property receiving laws. Ruling: {decision}."

    elif topic == "women_violence_marriage":
        if scenario == "domestic_violence_498a":
            return f"Synthetic Case: Application filed under the Protection of Women from Domestic Violence Act seeking protection orders, monetary relief, and right to shared household following emotional cruelty and physical exclusion. Respondents argued independent living status. {court_level} issued protection and residence orders based on proof of marital residence. Ruling: {decision}."
        elif scenario == "dowry_harassment":
            return f"Synthetic Case: Complaint alleging persistent demands for motor vehicles and cash post-marriage accompanied by social isolation and harassment. {court_level} reviewed corroborative statements from local residents, medical records, and communication records to evaluate cruelty and dowry demands. Ruling: {decision}."
        elif scenario == "maintenance_125_crpc":
            return f"Synthetic Case: Deserted spouse and minor child sought monthly maintenance under statutory provisions (CrPC Section 125 / BNSS Section 144). Respondent claimed lack of regular income despite holding {land} of agricultural land. {court_level} assessed imputed earning capacity based on asset ownership and awarded monthly maintenance. Ruling: {decision}."
        elif scenario == "child_custody":
            return f"Synthetic Case: Custody dispute over a 7-year-old child following marital separation. Father highlighted higher financial earnings, while mother demonstrated primary caregiving history and stable emotional environment. {court_level} ruled that paramount welfare of the minor child overrides financial superiority alone. Ruling: {decision}."
        elif scenario == "posh_workplace_harassment":
            return f"Synthetic Case: School teacher reported inappropriate physical gestures and verbal harassment by a senior administrator. Employer failed to constitute an Internal Complaints Committee as required under POSH legislation. {court_level} issued directions for setting up a compliant committee and interim protective transfer. Ruling: {decision}."
        elif scenario == "protection_orders":
            return f"Synthetic Case: Urgent prayer for protection order prohibiting an estranged spouse from approaching the applicant's workplace or residence during ongoing matrimonial litigation. {court_level} granted restraining orders enforcing non-contact and physical protection. Ruling: {decision}."
        elif scenario == "marital_property_rights":
            return f"Synthetic Case: Petition seeking recovery of Stridhan properties, including gold ornaments and financial gifts, retained by in-laws after separation. {court_level} re-affirmed that Stridhan is the exclusive property of the woman and directed full restitution. Ruling: {decision}."
        elif scenario == "restitution_conjugal_rights":
            return f"Synthetic Case: Petition filed for restitution of conjugal rights following marital separation. Respondent proved reasonable excuse based on continuous verbal cruelty and financial neglect. {court_level} dismissed restitution prayer. Ruling: {decision}."
        elif scenario == "interim_maintenance_enhancement":
            return f"Synthetic Case: Application seeking enhancement of interim maintenance due to rising educational costs of minor children and medical expenses. {court_level} verified respondent's revised income tax returns and enhanced monthly maintenance grant. Ruling: {decision}."
        elif scenario == "maternal_right_to_residence":
            return f"Synthetic Case: Aggrieved woman evicted from shared matrimonial home by in-laws during husband's overseas absence. {court_level} enforced statutory right of residence under domestic violence laws, ordering immediate re-entry and police protection. Ruling: {decision}."
        else:
            return f"Synthetic Case: Petition for dissolution of marriage on ground of continuous desertion for over 2 years without reasonable cause. {court_level} evaluated witness testimonies establishing intentional abandonment and granted decree. Ruling: {decision}."

    else:
        if scenario == "title_disputes":
            return f"Synthetic Case: Plaintiff claimed sole title over {land} of ancestral agricultural land based on an unregistered family partition deed, whereas defendant produced a registered sale deed from a co-sharer. {court_level} adjudicated title validity by applying registration requirements and revenue record entries. Ruling: {decision}."
        elif scenario == "land_acquisition_compensation":
            return f"Synthetic Case: Landowners challenged compensation awarded for highway land acquisition, contending that agricultural classification ignored nearby commercial development potential. {court_level} reassessed land valuation based on recent comparative sale exemplars and enhanced compensation. Ruling: {decision}."
        elif scenario == "tenancy_eviction":
            return f"Synthetic Case: Landlord sought eviction of agricultural tenant on grounds of non-payment of crop share. Tenant produced proof of severe drought declaration and statutory protection under rural tenancy legislation. {court_level} dismissed eviction prayer while structuring rent deferment. Ruling: {decision}."
        elif scenario == "boundary_disputes":
            return f"Synthetic Case: Adjoining landholders disputed a boundary buffer strip of {land}. Total station survey conducted by the revenue surveyor was submitted as evidence. {court_level} accepted official revenue boundary survey and directed physical demarcation with boundary pillars. Ruling: {decision}."
        elif scenario == "inheritance_partition":
            return f"Synthetic Case: Daughter filed suit for partition claiming equal share in ancestral joint family land under amended Hindu Succession provisions. Brothers claimed prior oral partition. {court_level} held that oral partition without registered documentation does not defeat statutory equal coparcenary rights. Ruling: {decision}."
        elif scenario == "encroachments":
            return f"Synthetic Case: Village Panchayat instituted eviction proceedings against unauthorized construction on community grazing land (Gauchar). Encroacher claimed long-standing occupation. {court_level} held community pasture land cannot be alienated or regularized and affirmed eviction orders. Ruling: {decision}."
        elif scenario == "adverse_possession":
            return f"Synthetic Case: Occupant claimed ownership over a residential plot through adverse possession, demonstrating continuous, peaceful, and open occupation for over 15 years without owner interruption. {court_level} evaluated hostile possession requirements and declared title. Ruling: {decision}."
        elif scenario == "government_land_allotment":
            return f"Synthetic Case: Allotment of agricultural land patta to a landless worker was cancelled by local authorities without issuing a show-cause notice. {court_level} quashed the cancellation for violating natural justice principles and restored the patta allotment. Ruling: {decision}."
        elif scenario == "easementary_rights_way":
            return f"Synthetic Case: Farm owner sought injunction against neighbor blocking traditional passage road connecting inner field plot to main cart track. {court_level} verified continuous prescription use for over 20 years and granted permanent easementary right of way. Ruling: {decision}."
        elif scenario == "mortgage_redemption_dispute":
            return f"Synthetic Case: Mortgagor filed suit for redemption of usufructuary mortgage over {land} of farmland upon full repayment of principal debt to moneylender. {court_level} directed possession restoration and mortgage deed discharge. Ruling: {decision}."
        elif scenario == "revenue_mutation_record_correction":
            return f"Synthetic Case: Petitioner challenged fraudulent mutation entry recorded in favor of third party in village revenue records (Khasra/Khatauni). {court_level} set aside erroneous revenue entry and directed correction based on registered title documents. Ruling: {decision}."
        elif scenario == "common_pasture_gauchar_dispute":
            return f"Synthetic Case: Residents challenged illegal conversion of village common pasture land into commercial allotment by local administrative committee. {court_level} re-affirmed public trust doctrine regarding common village assets and quashed commercial allotment. Ruling: {decision}."
        else:
            return f"Synthetic Case: Large landholder challenged state ceiling proceedings classifying surplus agricultural holdings for redistribution to landless families. {court_level} verified statutory ceiling limits and upheld surplus land declaration. Ruling: {decision}."

rows_per_topic = 250
all_topics = ["labour_rights", "crime", "women_violence_marriage", "land_dispute"]
prefix_map = {
    "labour_rights": "SYN_LAB",
    "crime": "SYN_CRI",
    "women_violence_marriage": "SYN_WOM",
    "land_dispute": "SYN_LAN"
}

total_rows = []

for topic in all_topics:
    scenarios = scenarios_map[topic]
    for i in range(1, rows_per_topic + 1):
        case_id = f"{prefix_map[topic]}_{i:04d}"
        scenario = scenarios[(i - 1) % len(scenarios)]
        court_level = court_levels[(i - 1) % len(court_levels)]
        decision = decisions[(i - 1) % len(decisions)]
        
        narrative = generate_case_narrative(topic, scenario, court_level, decision)
        
        total_rows.append({
            "case_id": case_id,
            "topic": topic,
            "scenario": scenario,
            "court_level": court_level,
            "text": narrative,
            "decision": decision,
            "is_synthetic": "True"
        })

output_file = "synthetic_case_examples_rag_1000.csv"
fieldnames = ["case_id", "topic", "scenario", "court_level", "text", "decision", "is_synthetic"]

with open(output_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(total_rows)

print(f"File successfully created: '{output_file}' ({len(total_rows)} rows)")