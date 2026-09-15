#include "Customer.h"

#include <iostream>

/*
 * Stage 1 driver.
 *
 * There is no menu, no file and no manager yet. The only goal is to prove
 * that the Customer class and the Date struct compile, construct correctly
 * and print what we expect. Everything here gets replaced in Stage 3.
 */
int main() {
    std::cout << "=== Customer Management System - Stage 1 ===\n\n";

    // Built with the parameterised constructor.
    Customer first(1001,
                   "Ishan Kanchan",
                   "9876543210",
                   "ishan@example.com",
                   "Alandi, Pune",
                   Date::today());

    // Built with the default constructor, then filled in through setters.
    Customer second;
    second.setName("Rahul Deshmukh");
    second.setPhone("9123456780");
    second.setEmail("rahul@example.com");
    second.setAddress("Kothrud, Pune");

    std::cout << first.toDisplayString() << "\n\n";
    std::cout << second.toDisplayString() << "\n\n";

    // Demonstrates that a setter really does change the stored value.
    first.setAddress("Chakan, Pune");
    std::cout << "After updating the address of customer "
              << first.getId() << ":\n"
              << first.getAddress() << '\n';

    return 0;
}
