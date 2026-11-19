from .mongodb_profiles import get_profile_store


if __name__ == "__main__":
    print(get_profile_store().seed())
