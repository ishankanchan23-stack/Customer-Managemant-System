#include "Customer.h"

#include <ctime>
#include <iomanip>
#include <sstream>

using namespace std;

// ---------------------------------------------------------------------------
// Date
// ---------------------------------------------------------------------------

Date::Date() : day(1), month(1), year(2000) {}

Date::Date(int day, int month, int year)
    : day(day), month(month), year(year) {}

Date Date::today() {
    time_t now = time(nullptr);
    tm* local = localtime(&now);

    // tm_mon counts from 0, and tm_year counts from 1900.
    return Date(local->tm_mday, local->tm_mon + 1, local->tm_year + 1900);
}

string Date::toString() const {
    ostringstream out;
    out << setfill('0')
        << setw(2) << day << '-'
        << setw(2) << month << '-'
        << setw(4) << year;
    return out.str();
}

// ---------------------------------------------------------------------------
// Customer
// ---------------------------------------------------------------------------

Customer::Customer()
    : id(0), name(""), phone(""), email(""), address(""), registrationDate() {}

Customer::Customer(int id,
                   const string& name,
                   const string& phone,
                   const string& email,
                   const string& address,
                   const Date& registrationDate)
    : id(id),
      name(name),
      phone(phone),
      email(email),
      address(address),
      registrationDate(registrationDate) {}

int Customer::getId() const { return id; }
string Customer::getName() const { return name; }
string Customer::getPhone() const { return phone; }
string Customer::getEmail() const { return email; }
string Customer::getAddress() const { return address; }
Date Customer::getRegistrationDate() const { return registrationDate; }

void Customer::setName(const string& name) { this->name = name; }
void Customer::setPhone(const string& phone) { this->phone = phone; }
void Customer::setEmail(const string& email) { this->email = email; }
void Customer::setAddress(const string& address) { this->address = address; }

string Customer::toDisplayString() const {
    ostringstream out;
    out << "Customer ID   : " << id << '\n'
        << "Name          : " << name << '\n'
        << "Phone         : " << phone << '\n'
        << "Email         : " << email << '\n'
        << "Address       : " << address << '\n'
        << "Registered On : " << registrationDate.toString();
    return out.str();
}
