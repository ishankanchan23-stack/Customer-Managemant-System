#ifndef CUSTOMER_H
#define CUSTOMER_H

#include <string>

/*
 * Date: a plain data holder for a calendar date.
 *
 * This is a struct, not a class, because there are no internal rules to
 * protect - it is just three numbers that travel together. Customer, by
 * contrast, is a class because its fields must stay valid and controlled.
 */
struct Date {
    int day;
    int month;
    int year;

    Date();                        // defaults to 01-01-2000
    Date(int day, int month, int year);

    static Date today();           // reads the system clock
    std::string toString() const;  // "15-09-2026"
};

/*
 * Customer: one customer record.
 *
 * All fields are private (encapsulation). The outside world reads them
 * through getters and changes them through setters. There is deliberately
 * no setId() - an ID is assigned once at creation and never changes.
 */
class Customer {
private:
    int id;
    std::string name;
    std::string phone;
    std::string email;
    std::string address;
    Date registrationDate;

public:
    // Default constructor - creates an empty placeholder record.
    Customer();

    // Parameterised constructor - the normal way to create a customer.
    Customer(int id,
             const std::string& name,
             const std::string& phone,
             const std::string& email,
             const std::string& address,
             const Date& registrationDate);

    // Getters. Marked const because reading must never modify the object.
    int getId() const;
    std::string getName() const;
    std::string getPhone() const;
    std::string getEmail() const;
    std::string getAddress() const;
    Date getRegistrationDate() const;

    // Setters for the fields that are allowed to change later.
    void setName(const std::string& name);
    void setPhone(const std::string& phone);
    void setEmail(const std::string& email);
    void setAddress(const std::string& address);

    // Builds a human-readable block of text describing this customer.
    // It returns a string instead of printing, so that Customer never
    // depends on the console - that stays the UI layer's job.
    std::string toDisplayString() const;
};

#endif // CUSTOMER_H
