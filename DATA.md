# india-vehicle-stats

The source data is fetched from the [Parivahan Vahan Sewa](https://vahan.parivahan.gov.in/vahan4dashboard/) portal, which provides comprehensive vehicle registration and transport permit statistics across India.

## Data Dictionary

| Variable | Type | Description |
|----------|------|-------------|
| State | string | Two-letter state/union territory code (e.g., KA for Karnataka, DL for Delhi) |
| RTO | int64 | Regional Transport Office numeric code (1-999) |
| RTO Name | string | Full name of the Regional Transport Office |
| Year | int64 | Year of the record (2021-2025) |
| Month | int64 | Month of the record (1-12) |
| Metric | string | Category of measurement being tracked |
| Name | string | Name of specific item/category within the metric |
| Count | int64 | Numerical value/count for the metric-name combination |

## Metric Categories

The dataset includes 11 different metric categories:

1. **Permit Category** (Private Bus Permit, Heavy Goods Vehicle (HGV), Light Goods Vehicle (LGV), Local Car Taxi Permit, etc.)
2. **Permit Purpose** (Fresh Permit, Permit Variation/Endorsement, Renewal of Permit, Special Permit, Temporary Permit, etc.)
3. **Permit Type** (Contract Carriage Permit, Goods Permit, Stage Carriage Permit, Private Service Vehicle Permit, All India Tourist Permit, etc.)
4. **Registration Category** (Vehicle categories including Heavy Goods Vehicle, Heavy Motor Vehicle, Heavy Passenger Vehicle, Light Goods Vehicle, Light Motor Vehicle, etc.)
5. **Registration Class** (Specific vehicle classes such as Agricultural Tractor, Ambulance, Bus, Construction Equipment Vehicle, etc.)
6. **Registration Fuel** (Fuel types including Diesel, Electric (BOV), Petrol, Petrol/Hybrid, Petrol/Ethanol, CNG, LPG, etc.)
7. **Registration Manufacturer** (Name of the vehicle manufacturer such as Maruti Suzuki India Pvt Ltd, Mahindra & Mahindra Limited, Bajaj Auto Ltd, etc.)
8. **Registration Standard** (Emission standards including Bharat Stage IV, Bharat Stage VI, Bharat (Trem) Stage III A, etc.)
9. **Revenue (Fee)** (Alteration of Motor Vehicle, Change of Address in RC, Conversion from Paper RC to Smart Card, Learner's License fees, Registration fees, etc.)
10. **Revenue (Tax)** (Tax collections including MV Tax (Motor Vehicle Tax), Labour Cess, Additional MV Tax, Road Safety Tax/Cess, etc.)
11. **Transaction** (Various RTO transactions including Add/Modify Nominee, Alteration of Motor Vehicle, NOC-related transactions, License renewals and conversions, etc.)

## Data Quality Notes

- Data is aggregated monthly by RTO and metric combinations
- Some records may contain missing or null values in categorical fields
- Individual counts may have slight mismatch (under 2.5%) compared to the latest counts reported on the Vahan Sewa portal