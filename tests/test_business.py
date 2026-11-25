from src.lead_intelligence.models.business import Business


def test_create_business():
    business = Business(
        name="Nepal Hiking Team",
        address="Thamel, Kathmandu, Nepal",
        phone_numbers=["+977123456789"],
        website="https://www.nepalhikingteam.com/",
    )

    assert business.name == "Nepal Hiking Team"
    assert business.phone_numbers == ["+977123456789"]
