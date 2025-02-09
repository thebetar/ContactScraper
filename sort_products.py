result = []

with open("products.txt", "r") as file:
    result = [line.strip().lower() for line in file]

    # Sort products
    result = list(set(result))
    result.sort()

    # Write sorted products to file
    with open("products.txt", "w") as file:
        for product in result:
            file.write(f"{product}\n")
